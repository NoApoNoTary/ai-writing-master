"""Small, append-friendly failure-case library for writing runs."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Iterable

from writing_master._runfs import RunFsError, run_directory, run_lock
from writing_master.personal_context import (
    ContextError,
    atomic_write_bytes,
    atomic_write_bytes_at,
    context_lock,
    read_bytes_at,
)

FAILURE_CASES_FILE = "failure-cases.jsonl"
SNAPSHOT_FILE = "failure-case-snapshot.md"
STATUSES = ("proposed", "active", "superseded")
REQUIRED_FIELDS = (
    "id", "status", "tags", "source_run", "source_session", "symptom",
    "root_cause", "guardrail", "audit_check",
)


class FailureCaseError(ContextError):
    """Stable failure-case contract error."""


def default_failure_cases_path(home: Path | str | None = None) -> Path:
    if home is None:
        home = os.getenv("WRITING_MASTER_HOME") or "~/.writing-master"
    return Path(home).expanduser() / FAILURE_CASES_FILE


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise FailureCaseError("invalid_input", f"{field} must be a non-empty string")
    return value.strip()


def _tags(value: object) -> list[str]:
    if not isinstance(value, (list, tuple, set)):
        raise FailureCaseError("invalid_input", "tags must be a list")
    result = []
    for item in value:
        tag = _text(item, "tag")
        if tag not in result:
            result.append(tag)
    return result


def validate_case(value: dict, *, allow_created_at: bool = True) -> dict:
    if not isinstance(value, dict):
        raise FailureCaseError("invalid_input", "failure case must be an object")
    if any(not isinstance(key, str) for key in value):
        raise FailureCaseError("invalid_input", "failure case keys must be strings")
    missing = [field for field in REQUIRED_FIELDS if field not in value]
    if missing:
        raise FailureCaseError("invalid_input", f"failure case missing fields: {', '.join(missing)}")
    case = dict(value)
    for field in (
        "id", "status", "source_run", "source_session", "symptom", "root_cause",
        "guardrail", "audit_check",
    ):
        case[field] = _text(value[field], field)
    case["tags"] = _tags(value["tags"])
    if case["status"] not in STATUSES:
        raise FailureCaseError("invalid_input", "status must be proposed, active, or superseded")
    if allow_created_at and "created_at" in value:
        case["created_at"] = _text(value["created_at"], "created_at")
    return case


def _read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise FailureCaseError("io_error", f"cannot read failure cases: {path}") from error
    cases = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
            cases.append(validate_case(value))
        except (json.JSONDecodeError, FailureCaseError) as error:
            raise FailureCaseError("invalid_json", f"invalid failure case line {number}") from error
    return cases


def _lock(path: Path):
    return context_lock(path.parent)

def _atomic_write(path: Path, text: str) -> None:
    try:
        atomic_write_bytes(path, text.encode("utf-8"))
    except ContextError as error:
        raise FailureCaseError(error.code, str(error)) from error


def _serialize(cases: list[dict]) -> str:
    try:
        return "".join(
            json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
            for item in cases
        )
    except (TypeError, ValueError) as error:
        raise FailureCaseError("invalid_input", "failure case extensions must be JSON values") from error

def list_cases(path: Path | str | None = None, *, status: str | None = None) -> list[dict]:
    target = Path(path).expanduser() if path is not None else default_failure_cases_path()
    cases = _read(target)
    if status is not None:
        if status not in STATUSES:
            raise FailureCaseError("invalid_input", "unsupported status")
        cases = [case for case in cases if case["status"] == status]
    return cases


def propose_case(case: dict, path: Path | str | None = None) -> dict:
    target = Path(path).expanduser() if path is not None else default_failure_cases_path()
    if not isinstance(case, dict):
        raise FailureCaseError("invalid_input", "failure case must be an object")
    candidate = validate_case({**case, "status": "proposed"})
    candidate.setdefault("created_at", datetime.now(timezone.utc).isoformat())
    with _lock(target):
        cases = _read(target)
        if any(item["id"] == candidate["id"] for item in cases):
            raise FailureCaseError("already_exists", f"failure case already exists: {candidate['id']}")
        _atomic_write(target, _serialize(cases + [candidate]))
    return candidate


def update_case_status(case_id: str, status: str, path: Path | str | None = None) -> dict:
    ident = _text(case_id, "id")
    if status not in STATUSES:
        raise FailureCaseError("invalid_input", "unsupported status")
    target = Path(path).expanduser() if path is not None else default_failure_cases_path()
    with _lock(target):
        cases = _read(target)
        for index, case in enumerate(cases):
            if case["id"] == ident:
                updated = dict(case, status=status)
                cases[index] = updated
                _atomic_write(target, _serialize(cases))
                return updated
    raise FailureCaseError("not_found", f"failure case not found: {ident}")


def select_cases(tags: Iterable[str] | None = None, *, limit: int = 5, path: Path | str | None = None) -> list[dict]:
    if type(limit) is not int or not 0 <= limit:
        raise FailureCaseError("invalid_input", "limit must be a non-negative integer")
    if limit == 0:
        return []
    wanted = set(_tags(list(tags))) if tags is not None else set()
    selected = []
    for case in list_cases(path, status="active"):
        if wanted and not wanted.intersection(case["tags"]):
            continue
        selected.append(case)
        if len(selected) >= limit:
            break
    return selected


def snapshot_markdown(cases: Iterable[dict]) -> str:
    cases = [validate_case(case) for case in cases]
    lines = ["# Failure Case Snapshot", ""]
    if not cases:
        lines.append("（本次没有匹配规则。）")
        return "\n".join(lines) + "\n"
    for case in cases:
        lines.extend([
            f"- guardrail: {case['guardrail']}",
            f"- audit_check: {case['audit_check']}",
            "",
        ])
    return "\n".join(lines)


def write_snapshot(run_dir: Path | str, *, tags: Iterable[str] | None = None, limit: int = 5, path: Path | str | None = None) -> dict:
    cases = select_cases(tags, limit=limit, path=path)
    try:
        with run_directory(run_dir) as (run_fd, _):
            with run_lock(run_fd):
                try:
                    read_bytes_at(run_fd, SNAPSHOT_FILE)
                except ContextError as error:
                    if error.code != "not_initialized":
                        raise
                atomic_write_bytes_at(run_fd, SNAPSHOT_FILE, snapshot_markdown(cases).encode("utf-8"))
    except (RunFsError, ContextError) as error:
        raise FailureCaseError(error.code, str(error)) from error
    return {"path": SNAPSHOT_FILE, "count": len(cases), "case_ids": [case["id"] for case in cases]}


class FailureCaseStore:
    """Thin API wrapper around one JSONL library path."""

    def __init__(self, path: Path | str | None = None):
        self.path = Path(path).expanduser() if path is not None else default_failure_cases_path()

    def propose(self, case: dict) -> dict:
        return propose_case(case, self.path)

    def set_status(self, case_id: str, status: str) -> dict:
        return update_case_status(case_id, status, self.path)

    def list(self, *, status: str | None = None) -> list[dict]:
        return list_cases(self.path, status=status)

    def select(self, tags: Iterable[str] | None = None, *, limit: int = 5) -> list[dict]:
        return select_cases(tags, limit=limit, path=self.path)

    def snapshot(self, run_dir: Path | str, *, tags: Iterable[str] | None = None, limit: int = 5) -> dict:
        return write_snapshot(run_dir, tags=tags, limit=limit, path=self.path)
