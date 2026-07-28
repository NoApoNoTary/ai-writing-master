"""Canonical, task-local Topic Research Brief persistence and validation.

The module validates the structure and provenance links of a Research Brief.
It deliberately does not judge whether an Agent's heat, audience, or editorial
judgement is true; those are Agent responsibilities backed by its evidence.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, timezone
import errno
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import secrets
import stat
from typing import Iterator
import unicodedata
from urllib.parse import urlsplit

from writing_master.personal_context import (
    ContextError,
    SNAPSHOT_FILE,
    canonical_sha256,
    normalized_content_sha256,
    validate_snapshot,
)


RESEARCH_BRIEF_SCHEMA_VERSION = 1
RESEARCH_BRIEF_FILE = "research-brief.json"
RESEARCH_BRIEF_DRAFT_FILE = "research-brief-draft.json"

_RFC3339 = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _error(code: str, message: str) -> None:
    raise ContextError(code, message)


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def _nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value)


def _safe_candidate_id(value: object) -> bool:
    """Accept human-readable IDs while excluding path/control characters."""
    return (
        isinstance(value, str)
        and bool(value)
        and value not in {".", ".."}
        and "/" not in value
        and "\\" not in value
        and "\x00" not in value
        and not any(character.isspace() for character in value)
        and not any(unicodedata.category(character) in {"Cc", "Cf", "Cs"} for character in value)
    )


def _parse_rfc3339(value: object, *, field: str) -> datetime:
    if not isinstance(value, str) or _RFC3339.fullmatch(value) is None:
        _error("invalid_input", f"{field} must be an RFC3339 timestamp with timezone")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError as error:
        raise ContextError("invalid_input", f"{field} must be an RFC3339 timestamp with timezone") from error
    if parsed.tzinfo is None:
        _error("invalid_input", f"{field} must include a timezone")
    try:
        return parsed.astimezone(timezone.utc)
    except (OverflowError, ValueError) as error:
        raise ContextError("invalid_input", f"{field} must be a valid RFC3339 instant") from error


def _utc_now(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if not isinstance(now, datetime) or now.tzinfo is None:
        _error("invalid_input", "now must be a timezone-aware datetime")
    try:
        return now.astimezone(timezone.utc)
    except (OverflowError, ValueError) as error:
        raise ContextError("invalid_input", "now must be a valid timezone-aware datetime") from error


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _valid_score_number(value: object) -> bool:
    if type(value) is int:
        return 0 <= value <= 10
    if type(value) is float:
        return math.isfinite(value) and 0 <= value <= 10
    return False


def _validate_score(value: object, *, name: str, author_fit: bool = False) -> None:
    expected = {"value", "rationale", "references"} if author_fit else {"value", "rationale"}
    if not isinstance(value, dict) or set(value) != expected:
        _error("invalid_input", f"scores.{name} has unsupported fields")
    score = value["value"]
    if not _valid_score_number(score):
        _error("invalid_input", f"scores.{name}.value must be a finite score from 0 to 10")
    if not _nonempty_string(value["rationale"]):
        _error("invalid_input", f"scores.{name}.rationale must be non-empty")


def make_evidence_id(evidence: dict) -> str:
    """Return the deterministic Evidence ID specified by the Goal C contract."""
    if not isinstance(evidence, dict):
        _error("invalid_input", "evidence must be an object")
    try:
        payload = {
            "source_url": evidence["source_url"],
            "source_date": evidence["source_date"],
            "content_sha256": evidence["content_sha256"],
        }
    except KeyError as error:
        raise ContextError("invalid_input", "evidence is missing stable-ID fields") from error
    return "evidence-" + canonical_sha256(payload)[:16]


def _validate_url(value: object) -> None:
    if not isinstance(value, str):
        _error("invalid_input", "evidence source_url must be an absolute HTTP(S) URL")
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        parsed.port
    except ValueError as error:
        raise ContextError("invalid_input", "evidence source_url must be an absolute HTTP(S) URL") from error
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or not hostname
        or any(char.isspace() for char in value)
    ):
        _error("invalid_input", "evidence source_url must be an absolute HTTP(S) URL")


def _validate_author_fit(references: object, snapshot: dict) -> None:
    if not isinstance(references, list) or not references:
        _error("invalid_input", "scores.author_fit.references must be a non-empty list")
    profile = snapshot["profile"]
    material_ids = {item["item_id"] for item in snapshot["materials"]}
    for reference in references:
        if not isinstance(reference, dict) or not isinstance(reference.get("kind"), str):
            _error("invalid_input", "author_fit reference is invalid")
        if reference["kind"] == "profile":
            expected = {"kind", "profile_id", "revision", "content_sha256"}
            if set(reference) != expected or type(reference.get("revision")) is not int or not _is_sha256(reference.get("content_sha256")):
                _error("invalid_input", "profile author_fit reference is invalid")
            if (
                reference["profile_id"] != profile["profile_id"]
                or reference["revision"] != profile["revision"]
                or reference["content_sha256"] != profile["content_sha256"]
            ):
                _error("hash_mismatch", "profile author_fit reference does not match the Snapshot")
        elif reference["kind"] == "material":
            if (
                set(reference) != {"kind", "item_id"}
                or not isinstance(reference.get("item_id"), str)
                or not reference["item_id"]
            ):
                _error("invalid_input", "material author_fit reference is invalid")
            if reference["item_id"] not in material_ids:
                _error("unknown_id", "author_fit references a material outside the Snapshot")
        else:
            _error("invalid_input", "author_fit reference kind is unsupported")


def _validate_evidence(candidate: dict, heat_time: datetime) -> None:
    evidence = candidate["evidence"]
    if not isinstance(evidence, list):
        _error("invalid_input", "candidate evidence must be a list")
    evidence_ids: set[str] = set()
    for item in evidence:
        fields = {
            "evidence_id", "source_url", "source_title", "publisher", "source_date",
            "observed_at", "evidence_text", "content_sha256",
        }
        if not isinstance(item, dict) or set(item) != fields:
            _error("invalid_input", "evidence has unsupported fields")
        if not _nonempty_string(item["evidence_id"]):
            _error("invalid_input", "evidence_id must be non-empty")
        _validate_url(item["source_url"])
        for field in ("source_title", "publisher", "evidence_text"):
            if not _nonempty_string(item[field]):
                _error("invalid_input", f"evidence {field} must be non-empty")
        if not isinstance(item["source_date"], str):
            _error("invalid_input", "evidence source_date must use YYYY-MM-DD")
        try:
            source_date = date.fromisoformat(item["source_date"])
        except ValueError as error:
            raise ContextError("invalid_input", "evidence source_date must use YYYY-MM-DD") from error
        if item["source_date"] != source_date.isoformat():
            _error("invalid_input", "evidence source_date must use YYYY-MM-DD")
        observed_at = _parse_rfc3339(item["observed_at"], field="evidence observed_at")
        if observed_at > heat_time:
            _error("invalid_input", "evidence observed_at must not follow heat.as_of")
        if source_date > heat_time.astimezone(timezone.utc).date():
            _error("invalid_input", "evidence source_date must not follow heat.as_of")
        if not _is_sha256(item["content_sha256"]):
            _error("invalid_input", "evidence content_sha256 is invalid")
        try:
            normalized_hash = normalized_content_sha256(item["evidence_text"])
        except UnicodeError as error:
            raise ContextError("invalid_input", "evidence_text must be valid UTF-8 Unicode") from error
        if item["content_sha256"] != normalized_hash:
            _error("hash_mismatch", "evidence content_sha256 does not match evidence_text")
        if item["evidence_id"] != make_evidence_id(item):
            _error("hash_mismatch", "evidence_id does not match stable evidence fields")
        if item["evidence_id"] in evidence_ids:
            _error("invalid_input", "candidate evidence IDs must be unique")
        evidence_ids.add(item["evidence_id"])

    heat_ids = candidate["heat"]["evidence_ids"]
    if not isinstance(heat_ids, list) or not heat_ids or any(not _nonempty_string(value) for value in heat_ids):
        _error("invalid_input", "heat.evidence_ids must be a non-empty list")
    if len(heat_ids) != len(set(heat_ids)):
        _error("invalid_input", "heat.evidence_ids must not contain duplicates")
    for evidence_id in heat_ids:
        if evidence_id not in evidence_ids:
            _error("unknown_id", "heat.evidence_ids references missing candidate evidence")


def _validate_candidates(candidates: object, snapshot: dict, *, runtime_time: datetime) -> None:
    if not isinstance(candidates, list) or not 3 <= len(candidates) <= 10:
        _error("invalid_input", "Research Brief requires between 3 and 10 candidates")
    candidate_ids: set[str] = set()
    expected_candidate = {"candidate_id", "topic", "heat", "audience", "angle", "evidence", "scores", "rationale"}
    for candidate in candidates:
        if not isinstance(candidate, dict) or set(candidate) != expected_candidate:
            _error("invalid_input", "candidate has unsupported fields")
        if not _safe_candidate_id(candidate["candidate_id"]):
            _error("invalid_input", "candidate_id must be non-empty and safe")
        if candidate["candidate_id"] in candidate_ids:
            _error("invalid_input", "candidate IDs must be unique")
        candidate_ids.add(candidate["candidate_id"])
        for field in ("topic", "audience", "angle", "rationale"):
            if not _nonempty_string(candidate[field]):
                _error("invalid_input", f"candidate {field} must be non-empty")

        heat = candidate["heat"]
        if not isinstance(heat, dict) or set(heat) != {"score", "basis", "as_of", "evidence_ids"}:
            _error("invalid_input", "candidate heat has unsupported fields")
        if not _valid_score_number(heat["score"]):
            _error("invalid_input", "heat.score must be a finite score from 0 to 10")
        if not _nonempty_string(heat["basis"]):
            _error("invalid_input", "heat.basis must be non-empty")
        heat_time = _parse_rfc3339(heat["as_of"], field="heat.as_of")
        if heat_time > runtime_time:
            _error("invalid_input", "heat.as_of must not be in the future")

        scores = candidate["scores"]
        if not isinstance(scores, dict) or set(scores) != {"heat", "user_value", "differentiation", "author_fit"}:
            _error("invalid_input", "candidate scores must contain exactly four dimensions")
        _validate_score(scores["heat"], name="heat")
        _validate_score(scores["user_value"], name="user_value")
        _validate_score(scores["differentiation"], name="differentiation")
        _validate_score(scores["author_fit"], name="author_fit", author_fit=True)
        if heat["score"] != scores["heat"]["value"]:
            _error("invalid_input", "heat.score must equal scores.heat.value")
        _validate_author_fit(scores["author_fit"]["references"], snapshot)
        _validate_evidence(candidate, heat_time)


def validate_research_brief_draft(
    document: dict,
    snapshot: dict,
    *,
    now: datetime | None = None,
) -> None:
    """Validate Agent-owned draft fields against the frozen task Snapshot."""
    validate_snapshot(snapshot)
    runtime_time = _utc_now(now)
    if (
        not isinstance(document, dict)
        or set(document) != {"schema_version", "candidates"}
        or type(document.get("schema_version")) is not int
        or document["schema_version"] != RESEARCH_BRIEF_SCHEMA_VERSION
    ):
        _error("invalid_input", "unsupported Research Brief draft")
    _validate_candidates(document["candidates"], snapshot, runtime_time=runtime_time)
    _canonical_json_bytes(document)


def _canonical_created_at(document: object) -> datetime:
    expected = {"schema_version", "task_id", "created_at", "inputs", "candidates", "research_brief_sha256"}
    if (
        not isinstance(document, dict)
        or set(document) != expected
        or type(document.get("schema_version")) is not int
        or document["schema_version"] != RESEARCH_BRIEF_SCHEMA_VERSION
        or not _nonempty_string(document.get("task_id"))
    ):
        _error("schema_unsupported", "unsupported canonical Research Brief")
    try:
        return _parse_rfc3339(document["created_at"], field="Research Brief created_at")
    except ContextError as error:
        raise ContextError(
            "schema_unsupported", "canonical Research Brief created_at is invalid"
        ) from error


def validate_research_brief(
    document: dict,
    snapshot: dict,
    *,
    now: datetime | None = None,
) -> None:
    """Validate one persisted canonical Research Brief without reading the run."""
    validate_snapshot(snapshot)
    runtime_time = _utc_now(now)
    created_at = _canonical_created_at(document)
    if document["task_id"] != snapshot["task_id"]:
        _error("hash_mismatch", "Research Brief task_id does not match the Snapshot")
    if created_at > runtime_time:
        _error("invalid_input", "Research Brief created_at must not be in the future")
    inputs = document["inputs"]
    if not isinstance(inputs, dict) or set(inputs) != {"brief", "personal_context"}:
        _error("schema_unsupported", "canonical Research Brief inputs are invalid")
    brief = inputs["brief"]
    context = inputs["personal_context"]
    if (
        not isinstance(brief, dict) or set(brief) != {"path", "sha256"}
        or brief.get("path") != "brief.md" or not _is_sha256(brief.get("sha256"))
        or not isinstance(context, dict) or set(context) != {"path", "snapshot_sha256"}
        or context.get("path") != SNAPSHOT_FILE or not _is_sha256(context.get("snapshot_sha256"))
    ):
        _error("schema_unsupported", "canonical Research Brief inputs are invalid")
    if context["snapshot_sha256"] != snapshot["snapshot_sha256"]:
        _error("hash_mismatch", "Research Brief Snapshot hash does not match the Snapshot")
    _validate_candidates(document["candidates"], snapshot, runtime_time=created_at)
    if not _is_sha256(document.get("research_brief_sha256")):
        _error("schema_unsupported", "Research Brief self hash is invalid")
    expected_hash = canonical_sha256({key: value for key, value in document.items() if key != "research_brief_sha256"})
    if document["research_brief_sha256"] != expected_hash:
        _error("hash_mismatch", "Research Brief self hash does not match")


def _local_name(value: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value in {".", ".."}
        or "/" in value
        or "\\" in value
        or "\x00" in value
    ):
        _error("path_escape", "managed file name is unsafe")
    return value


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant: {value}")


def _canonical_json_bytes(value: dict) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as error:
        raise ContextError("invalid_input", "Research Brief is not canonical JSON") from error


@contextmanager
def _run_directory_fd(run_dir: Path | str) -> Iterator[int]:
    if not isinstance(run_dir, (str, os.PathLike)) or not os.fspath(run_dir):
        _error("invalid_input", "run_dir must be a non-empty path")
    try:
        path = Path(run_dir).expanduser()
    except (OSError, RuntimeError, ValueError) as error:
        raise ContextError("path_escape", "run directory is unsafe") from error
    parts = path.parts[1:] if path.is_absolute() else path.parts
    if any(part in {".", ".."} for part in parts):
        _error("path_escape", "run directory contains an unsafe path component")
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    start = path.anchor if path.is_absolute() else "."
    try:
        descriptor = os.open(start, flags)
    except FileNotFoundError as error:
        raise ContextError("not_initialized", "run directory is missing") from error
    except (OSError, ValueError) as error:
        raise ContextError("path_escape", "run directory is unsafe") from error
    try:
        for part in parts:
            try:
                next_descriptor = os.open(part, flags, dir_fd=descriptor)
            except FileNotFoundError as error:
                raise ContextError("not_initialized", "run directory is missing") from error
            except (OSError, ValueError) as error:
                try:
                    mode = os.stat(part, dir_fd=descriptor, follow_symlinks=False).st_mode
                except FileNotFoundError as missing:
                    raise ContextError("not_initialized", "run directory is missing") from missing
                except (OSError, ValueError) as inspect_error:
                    raise ContextError("path_escape", "run directory is unsafe") from inspect_error
                if stat.S_ISLNK(mode):
                    raise ContextError("path_escape", "run directory contains a symlink") from error
                if getattr(error, "errno", None) in {errno.ENOTDIR, errno.ENOENT}:
                    raise ContextError("not_initialized", "run directory is missing") from error
                raise ContextError("path_escape", "run directory is unsafe") from error
            os.close(descriptor)
            descriptor = next_descriptor
        yield descriptor
    finally:
        os.close(descriptor)


def _read_json_at(run_fd: int, name: str) -> dict:
    name = _local_name(name)
    descriptor = _open_regular_at(run_fd, name)
    try:
        with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
            text = handle.read()
        value = json.loads(text, parse_constant=_reject_json_constant)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as error:
        raise ContextError("invalid_json", f"invalid JSON document: {name}") from error
    if not isinstance(value, dict):
        _error("invalid_json", f"JSON object required: {name}")
    return value


def _open_regular_at(run_fd: int, name: str) -> int:
    name = _local_name(name)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        descriptor = os.open(name, flags, dir_fd=run_fd)
    except FileNotFoundError as error:
        raise ContextError("not_initialized", f"missing managed file: {name}") from error
    except OSError as error:
        raise ContextError("path_escape", f"unsafe managed file: {name}") from error
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            _error("path_escape", f"managed file must be regular: {name}")
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _read_bytes_at(run_fd: int, name: str) -> bytes:
    name = _local_name(name)
    descriptor = _open_regular_at(run_fd, name)
    try:
        with os.fdopen(descriptor, "rb") as handle:
            return handle.read()
    except OSError as error:
        raise ContextError("hash_mismatch", f"cannot read managed file: {name}") from error


def _file_exists_at(run_fd: int, name: str) -> bool:
    name = _local_name(name)
    try:
        os.stat(name, dir_fd=run_fd, follow_symlinks=False)
    except FileNotFoundError:
        return False
    except OSError as error:
        raise ContextError("path_escape", f"unsafe managed file: {name}") from error
    return True


def _publish_json_once_at(run_fd: int, name: str, value: dict) -> bool:
    """Publish canonical JSON only if *name* does not already exist.

    ``link`` creates the destination atomically and refuses to replace an
    existing path.  This remains write-once even if a compromised advisory
    lock splits contenders across different lock inodes.
    """
    name = _local_name(name)
    payload = _canonical_json_bytes(value)
    temporary = None
    descriptor = None
    try:
        for _ in range(100):
            candidate = f".{name}.{secrets.token_hex(16)}"
            try:
                descriptor = os.open(
                    candidate,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                    0o600,
                    dir_fd=run_fd,
                )
                temporary = candidate
                break
            except FileExistsError:
                continue
        if descriptor is None or temporary is None:
            _error("invalid_input", f"cannot allocate temporary file for {name}")
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = None
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(
                temporary,
                name,
                src_dir_fd=run_fd,
                dst_dir_fd=run_fd,
                follow_symlinks=False,
            )
        except FileExistsError:
            os.unlink(temporary, dir_fd=run_fd)
            temporary = None
            os.fsync(run_fd)
            return False
        os.unlink(temporary, dir_fd=run_fd)
        temporary = None
        os.fsync(run_fd)
        return True
    except BaseException:
        if descriptor is not None:
            os.close(descriptor)
        if temporary is not None:
            try:
                os.unlink(temporary, dir_fd=run_fd)
            except FileNotFoundError:
                pass
        raise


def _load_inputs(run_fd: int) -> tuple[str, dict, str, str]:
    status = _read_json_at(run_fd, "status.json")
    snapshot = _read_json_at(run_fd, SNAPSHOT_FILE)
    validate_snapshot(snapshot)
    task_id = status.get("task_id") if isinstance(status, dict) else None
    if not _nonempty_string(task_id):
        _error("invalid_input", "run directory has no valid task_id")
    if task_id != snapshot["task_id"]:
        _error("hash_mismatch", "status task_id does not match the Snapshot")
    brief_hash = hashlib.sha256(_read_bytes_at(run_fd, "brief.md")).hexdigest()
    return task_id, snapshot, brief_hash, snapshot["snapshot_sha256"]


def _assert_lock_integrity(run_fd: int, lock_fd: int) -> None:
    """Ensure the visible lock path still names the inode held by this process."""
    try:
        named = os.stat(".research-brief.lock", dir_fd=run_fd, follow_symlinks=False)
    except FileNotFoundError as error:
        raise ContextError("path_escape", "Research Brief lock changed while held") from error
    except OSError as error:
        raise ContextError("path_escape", "Research Brief lock is unsafe") from error
    held = os.fstat(lock_fd)
    if (
        not stat.S_ISREG(named.st_mode)
        or not stat.S_ISREG(held.st_mode)
        or (named.st_dev, named.st_ino) != (held.st_dev, held.st_ino)
    ):
        _error("path_escape", "Research Brief lock changed while held")


@contextmanager
def _research_brief_lock(run_fd: int) -> Iterator[int]:
    flags = (
        os.O_CREAT
        | os.O_RDWR
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        descriptor = os.open(".research-brief.lock", flags, 0o600, dir_fd=run_fd)
    except OSError as error:
        raise ContextError("path_escape", "Research Brief lock is unsafe") from error
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            _error("path_escape", "Research Brief lock must be a regular file")
    except BaseException:
        os.close(descriptor)
        raise
    with os.fdopen(descriptor, "a+", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            _assert_lock_integrity(run_fd, handle.fileno())
            yield handle.fileno()
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _canonical_document(
    *, task_id: str, created_at: datetime, brief_hash: str, snapshot_hash: str, draft: dict
) -> dict:
    document = {
        "schema_version": RESEARCH_BRIEF_SCHEMA_VERSION,
        "task_id": task_id,
        "created_at": _timestamp(created_at),
        "inputs": {
            "brief": {"path": "brief.md", "sha256": brief_hash},
            "personal_context": {"path": SNAPSHOT_FILE, "snapshot_sha256": snapshot_hash},
        },
        "candidates": draft["candidates"],
    }
    document["research_brief_sha256"] = canonical_sha256(document)
    return document


def _existing_research_brief_or_duplicate(
    run_fd: int,
    *,
    task_id: str,
    snapshot: dict,
    expected_inputs: dict,
    draft: dict,
) -> dict:
    existing = _read_json_at(run_fd, RESEARCH_BRIEF_FILE)
    existing_created_at = _canonical_created_at(existing)
    validate_research_brief(existing, snapshot, now=existing_created_at)
    validate_research_brief_draft(draft, snapshot, now=existing_created_at)
    if (
        existing["task_id"] == task_id
        and existing["inputs"] == expected_inputs
        and existing["candidates"] == draft["candidates"]
    ):
        return existing
    _error("duplicate", "a different write-once Research Brief already exists")


def save_research_brief(
    run_dir: Path | str,
    draft: dict,
    *,
    now: datetime | None = None,
) -> dict:
    """Validate and persist one write-once canonical Research Brief for a task."""
    created_at = _utc_now(now)
    with _run_directory_fd(run_dir) as run_fd:
        with _research_brief_lock(run_fd) as lock_fd:
            task_id, snapshot, brief_hash, snapshot_hash = _load_inputs(run_fd)
            expected_inputs = {
                "brief": {"path": "brief.md", "sha256": brief_hash},
                "personal_context": {"path": SNAPSHOT_FILE, "snapshot_sha256": snapshot_hash},
            }
            if _file_exists_at(run_fd, RESEARCH_BRIEF_FILE):
                return _existing_research_brief_or_duplicate(
                    run_fd,
                    task_id=task_id,
                    snapshot=snapshot,
                    expected_inputs=expected_inputs,
                    draft=draft,
                )

            validate_research_brief_draft(draft, snapshot, now=created_at)
            proposed = _canonical_document(
                task_id=task_id,
                created_at=created_at,
                brief_hash=brief_hash,
                snapshot_hash=snapshot_hash,
                draft=draft,
            )
            validate_research_brief(proposed, snapshot, now=created_at)
            _assert_lock_integrity(run_fd, lock_fd)
            if _publish_json_once_at(run_fd, RESEARCH_BRIEF_FILE, proposed):
                return proposed
            return _existing_research_brief_or_duplicate(
                run_fd,
                task_id=task_id,
                snapshot=snapshot,
                expected_inputs=expected_inputs,
                draft=draft,
            )


def verify_research_brief(
    run_dir: Path | str,
    *,
    now: datetime | None = None,
) -> dict:
    """Verify canonical structure plus the run's current Brief and Snapshot inputs."""
    check_time = _utc_now(now)
    with _run_directory_fd(run_dir) as run_fd:
        task_id, snapshot, brief_hash, snapshot_hash = _load_inputs(run_fd)
        document = _read_json_at(run_fd, RESEARCH_BRIEF_FILE)
        validate_research_brief(document, snapshot, now=check_time)
        if (
            document["task_id"] != task_id
            or document["inputs"]["brief"]["sha256"] != brief_hash
            or document["inputs"]["personal_context"]["snapshot_sha256"] != snapshot_hash
        ):
            _error("hash_mismatch", "Research Brief inputs have changed")
        return {
            "task_id": document["task_id"],
            "candidate_count": len(document["candidates"]),
            "research_brief_sha256": document["research_brief_sha256"],
            "verified": True,
        }
