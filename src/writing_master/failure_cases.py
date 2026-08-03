"""Small, append-friendly failure-case library for writing runs."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Iterable

from writing_master.personal_context import ContextError, atomic_write_bytes, context_lock

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
    missing = [field for field in REQUIRED_FIELDS if field not in value]
    if missing:
        raise FailureCaseError("invalid_input", f"failure case missing fields: {', '.join(missing)}")
    case = {
        "id": _text(value["id"], "id"),
        "status": _text(value["status"], "status"),
        "tags": _tags(value["tags"]),
        "source_run": _text(value["source_run"], "source_run"),
        "source_session": _text(value["source_session"], "source_session"),
        "symptom": _text(value["symptom"], "symptom"),
        "root_cause": _text(value["root_cause"], "root_cause"),
        "guardrail": _text(value["guardrail"], "guardrail"),
        "audit_check": _text(value["audit_check"], "audit_check"),
    }
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
    atomic_write_bytes(path, text.encode("utf-8"))

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
    candidate = validate_case({**case, "status": "proposed"})
    candidate.setdefault("created_at", datetime.now(timezone.utc).isoformat())
    with _lock(target):
        cases = _read(target)
        if any(item["id"] == candidate["id"] for item in cases):
            raise FailureCaseError("already_exists", f"failure case already exists: {candidate['id']}")
        _atomic_write(target, "".join(json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for item in cases + [candidate]))
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
                _atomic_write(target, "".join(json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for item in cases))
                return updated
    raise FailureCaseError("not_found", f"failure case not found: {ident}")


def select_cases(tags: Iterable[str] | None = None, *, limit: int = 5, path: Path | str | None = None) -> list[dict]:
    if type(limit) is not int or not 0 <= limit:
        raise FailureCaseError("invalid_input", "limit must be a non-negative integer")
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
    lines = ["# Failure Case Snapshot", "", "仅注入选中案例的 guardrail 与 audit check；不包含历史会话。", ""]
    if not cases:
        lines.append("（本次没有匹配的 active failure case。）")
        return "\n".join(lines) + "\n"
    for case in cases:
        lines.extend([
            f"## {case['id']}",
            f"- tags: {', '.join(case['tags']) or '（无）'}",
            f"- guardrail: {case['guardrail']}",
            f"- audit_check: {case['audit_check']}",
            "",
        ])
    return "\n".join(lines)


def write_snapshot(run_dir: Path | str, *, tags: Iterable[str] | None = None, limit: int = 5, path: Path | str | None = None) -> dict:
    run = Path(run_dir).expanduser()
    if not run.is_dir():
        raise FailureCaseError("not_initialized", f"run directory is missing: {run}")
    cases = select_cases(tags, limit=limit, path=path)
    output = run / SNAPSHOT_FILE
    _atomic_write(output, snapshot_markdown(cases))
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
