"""Deterministic, file-backed handoffs for deep writing runs."""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import stat
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

import fcntl

from writing_master._runfs import RunFsError, resolved_run_directory, run_directory, run_lock
from writing_master.personal_context import ContextError, read_json_at
from writing_master.voice_presets import VoiceError, validate_snapshot


SCHEMA_VERSION = 1
ROLES = {"lead", "researcher", "editorial_strategist", "writer", "auditor"}
FAILURE_TYPES = {"input_error", "host_failure", "role_failure", "output_validation", "cancelled"}
VOICE_SNAPSHOT_FILE = "voice-profile-snapshot.json"
VOICE_ROLES = {"writer", "auditor"}
VOICE_FREE_ROLES = {"researcher", "editorial_strategist"}
TRANSITIONS = {
    "prepared": {"running", "stale"},
    "running": {"completed", "failed", "stale"},
    "completed": set(),
    "failed": set(),
    "stale": set(),
}


class HandoffError(ValueError):
    """A contract, state, or filesystem boundary violation."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_relative_file_at(run_fd: int, relative: str) -> str:
    """Hash one regular run-local file without reopening the run path."""
    parts = PurePosixPath(_relative_path(relative)).parts
    directory_fd = os.dup(run_fd)
    descriptor = None
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        for part in parts[:-1]:
            try:
                next_fd = os.open(part, directory_flags, dir_fd=directory_fd)
            except OSError as error:
                raise HandoffError(f"missing or invalid input: {relative}") from error
            os.close(directory_fd)
            directory_fd = next_fd
        try:
            descriptor = os.open(
                parts[-1],
                os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0),
                dir_fd=directory_fd,
            )
        except OSError as error:
            raise HandoffError(f"missing or invalid input: {relative}") from error
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise HandoffError(f"input is not a file: {relative}")
        digest = hashlib.sha256()
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = None
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(directory_fd)


def _json_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise HandoffError(f"invalid JSON: {path}") from error
    if not isinstance(value, dict):
        raise HandoffError(f"JSON object required: {path}")
    return value


def atomic_write_json(path: Path, value: dict) -> None:
    """Durably replace one JSON file without exposing a partial document."""
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _atomic_write_json_at(directory_fd: int, name: str, value: dict) -> None:
    """Durably replace one JSON file relative to an already-open directory."""
    encoded = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    descriptor = None
    temporary = None
    try:
        for _ in range(100):
            candidate = f".{name}.{secrets.token_hex(16)}"
            try:
                descriptor = os.open(
                    candidate,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                    0o600,
                    dir_fd=directory_fd,
                )
                temporary = candidate
                break
            except FileExistsError:
                continue
        if descriptor is None or temporary is None:
            raise HandoffError(f"cannot allocate temporary file for {name}")
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = None
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, name, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
        temporary = None
        os.fsync(directory_fd)
    except BaseException:
        if descriptor is not None:
            os.close(descriptor)
        if temporary is not None:
            try:
                os.unlink(temporary, dir_fd=directory_fd)
            except FileNotFoundError:
                pass
        raise


@contextmanager
def _directory_at(parent_fd: int, name: str, *, create: bool = False):
    """Open one direct child directory without following a symlink."""
    if not isinstance(name, str) or not name or "/" in name or "\\" in name or name in {".", ".."}:
        raise HandoffError(f"unsafe managed directory: {name}")
    if create:
        try:
            os.mkdir(name, 0o700, dir_fd=parent_fd)
        except FileExistsError:
            pass
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(name, flags, dir_fd=parent_fd)
    except OSError as error:
        raise HandoffError(f"unsafe managed directory: {name}") from error
    try:
        yield descriptor
    finally:
        os.close(descriptor)


@contextmanager
def _anchored_run_directory(run_dir: Path | str):
    try:
        with run_directory(run_dir) as anchored:
            yield anchored
    except RunFsError as error:
        raise HandoffError(str(error)) from error


@contextmanager
def _new_attempt_directory(run_fd: int, run_dir: Path, phase: str, to_role: str):
    """Create and anchor the next attempt below the real run directory."""
    with _directory_at(run_fd, "handoffs", create=True) as handoffs_fd:
        stage_name = f"{phase}-{to_role}"
        with _directory_at(handoffs_fd, stage_name, create=True) as stage_fd:
            attempts = []
            for name in os.listdir(stage_fd):
                suffix = name.removeprefix("attempt-")
                if not name.startswith("attempt-") or not suffix.isdigit():
                    continue
                try:
                    metadata = os.stat(name, dir_fd=stage_fd, follow_symlinks=False)
                except OSError as error:
                    raise HandoffError("cannot inspect handoff attempts") from error
                if stat.S_ISDIR(metadata.st_mode):
                    attempts.append(int(suffix))
            attempt = max(attempts, default=0) + 1
            attempt_name = f"attempt-{attempt:02d}"
            try:
                os.mkdir(attempt_name, 0o700, dir_fd=stage_fd)
            except OSError as error:
                raise HandoffError("cannot create handoff attempt") from error
            with _directory_at(stage_fd, attempt_name) as attempt_fd:
                try:
                    os.mkdir("outputs", 0o700, dir_fd=attempt_fd)
                except OSError as error:
                    raise HandoffError("cannot create handoff output directory") from error
                yield attempt, _attempt_dir(run_dir, phase, to_role, attempt), attempt_fd


@contextmanager
def _lock(run_dir: Path):
    run_dir.mkdir(parents=True, exist_ok=True)
    with (run_dir / ".handoff.lock").open("a+") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


@contextmanager
def _lock_fd(run_fd: int):
    try:
        with run_lock(run_fd):
            yield
    except RunFsError as error:
        raise HandoffError(str(error)) from error


def _relative_path(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise HandoffError("non-empty relative path required")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise HandoffError(f"unsafe relative path: {value}")
    return path.as_posix()


def _slug(value: str, name: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", value):
        raise HandoffError(f"{name} must be a safe slug")
    return value


def safe_path(root: Path, relative: str, *, must_exist: bool = False) -> Path:
    """Resolve a contract path and reject paths or symlinks outside ``root``."""
    relative = _relative_path(relative)
    root = root.resolve()
    candidate = root / relative
    try:
        resolved = candidate.resolve(strict=must_exist)
    except OSError as error:
        raise HandoffError(f"missing or invalid path: {relative}") from error
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise HandoffError(f"path escapes run directory: {relative}") from error
    return candidate


def _require_strings(value: object, name: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        raise HandoffError(f"{name} must be a non-empty list")
    if not all(isinstance(item, str) and item for item in value):
        raise HandoffError(f"{name} must contain strings")
    return value


def validate_manifest(manifest: dict, run_dir: Path | None = None) -> None:
    required = {
        "schema_version", "handoff_id", "task_id", "attempt", "from_role", "to_role", "phase",
        "objective", "decision_to_inform", "allowed_inputs", "forbidden_inputs", "write_scope",
        "expected_outputs", "done_criteria", "status", "output_root", "result_path", "role_card",
    }
    missing = required - manifest.keys()
    if missing or manifest.get("schema_version") != SCHEMA_VERSION:
        raise HandoffError(f"invalid manifest schema: missing={sorted(missing)}")
    if manifest["from_role"] not in ROLES or manifest["to_role"] not in ROLES:
        raise HandoffError("unknown handoff role")
    if not isinstance(manifest["attempt"], int) or manifest["attempt"] < 1:
        raise HandoffError("attempt must be a positive integer")
    if manifest["status"] != "prepared":
        raise HandoffError("manifest status must be prepared")
    for key in ("handoff_id", "task_id", "phase", "objective", "decision_to_inform", "role_card"):
        if not isinstance(manifest[key], str) or not manifest[key]:
            raise HandoffError(f"{key} must be a non-empty string")
    _require_strings(manifest["forbidden_inputs"], "forbidden_inputs", allow_empty=True)
    for key in ("write_scope", "expected_outputs", "done_criteria"):
        _require_strings(manifest[key], key)
    for path in manifest["write_scope"] + manifest["expected_outputs"]:
        _relative_path(path)
    for key in ("output_root", "result_path"):
        _relative_path(manifest[key])
    if not isinstance(manifest["allowed_inputs"], list):
        raise HandoffError("allowed_inputs must be a list")
    for item in manifest["allowed_inputs"]:
        if not isinstance(item, dict) or set(item) != {"path", "sha256", "required"}:
            raise HandoffError("invalid allowed input")
        path = _relative_path(item["path"])
        if not isinstance(item["sha256"], str) or len(item["sha256"]) != 64:
            raise HandoffError("invalid input sha256")
        if not isinstance(item["required"], bool):
            raise HandoffError("input required must be boolean")
        if run_dir:
            safe_path(run_dir, path, must_exist=True)


def _result_outputs(result: dict, manifest: dict) -> list[dict]:
    """Normalize logical records and explicit attempt-output paths."""
    if not isinstance(result["outputs"], list):
        raise HandoffError("outputs must be a list")
    normalized = []
    for item in result["outputs"]:
        if not isinstance(item, dict):
            raise HandoffError("invalid output record")
        if set(item) == {"path", "sha256"}:
            logical = _relative_path(item["path"])
        elif set(item) == {"logical_name", "path", "sha256"}:
            logical = _relative_path(item["logical_name"])
            actual = _relative_path(item["path"])
            expected = f"{manifest['output_root']}/{logical}"
            attempt_relative = f"{PurePosixPath(manifest['output_root']).name}/{logical}"
            if actual not in {expected, attempt_relative}:
                raise HandoffError("actual output path is outside output_root")
        else:
            raise HandoffError("invalid output record")
        if not isinstance(item["sha256"], str) or len(item["sha256"]) != 64:
            raise HandoffError("invalid output sha256")
        normalized.append({"path": logical, "sha256": item["sha256"]})
    return normalized


def validate_result(result: dict, manifest: dict) -> None:
    required = {"schema_version", "handoff_id", "attempt", "agent_ref", "status", "outputs", "blocking_issues", "summary", "completed_at"}
    missing = required - result.keys()
    if missing or result.get("schema_version") != SCHEMA_VERSION:
        raise HandoffError(f"invalid result schema: missing={sorted(missing)}")
    if result["handoff_id"] != manifest["handoff_id"] or result["attempt"] != manifest["attempt"]:
        raise HandoffError("result belongs to a different handoff")
    if result["status"] not in {"completed", "failed"}:
        raise HandoffError("result status must be completed or failed")
    for key in ("agent_ref", "summary", "completed_at"):
        if not isinstance(result[key], str) or not result[key]:
            raise HandoffError(f"result {key} must be a non-empty string")
    if not isinstance(result["blocking_issues"], list) or not all(isinstance(x, str) for x in result["blocking_issues"]):
        raise HandoffError("blocking_issues must be a list of strings")
    if result["status"] == "failed":
        if result.get("failure_type") not in FAILURE_TYPES:
            raise HandoffError("failed result requires a known failure_type")
        return
    if "failure_type" in result:
        raise HandoffError("completed result must not include failure_type")
    output_paths = [item["path"] for item in _result_outputs(result, manifest)]
    if set(output_paths) != set(manifest["expected_outputs"]):
        raise HandoffError("result outputs must exactly match expected_outputs")


def _within_scope(path: str, scopes: list[str]) -> bool:
    return any(path == scope or path.startswith(scope + "/") for scope in scopes)


def _attempt_dir(run_dir: Path, phase: str, to_role: str, attempt: int) -> Path:
    return run_dir / "handoffs" / f"{phase}-{to_role}" / f"attempt-{attempt:02d}"


def _status(run_dir: Path) -> dict:
    path = run_dir / "status.json"
    if not path.is_file():
        raise HandoffError("status.json is required before a handoff")
    status = _read_json(path)
    if status.get("mode") != "deep" or status.get("execution") != "multi_agent":
        raise HandoffError("handoffs require status mode=deep and execution=multi_agent")
    if not isinstance(status.get("task_id"), str) or not status["task_id"]:
        raise HandoffError("status.json requires task_id")
    return status


def _write_status(run_dir: Path, status: dict) -> None:
    atomic_write_json(run_dir / "status.json", status)


def _voice_scoped_inputs(status: dict, to_role: str, inputs: list[str]) -> list[str]:
    """Apply the task Voice boundary before manifest hashes are frozen."""
    scoped = list(inputs)
    state = status.get("voice_snapshot")
    if to_role in VOICE_FREE_ROLES and VOICE_SNAPSHOT_FILE in scoped:
        raise HandoffError(f"{to_role} must not receive {VOICE_SNAPSHOT_FILE}")
    if state not in {None, "pending", "ready", "legacy", "unavailable"}:
        raise HandoffError("status.json has an invalid Voice Snapshot state")
    if state == "pending" and to_role in VOICE_ROLES:
        raise HandoffError("Voice Snapshot must be ready before Writer or Auditor handoff")
    if state != "ready":
        if VOICE_SNAPSHOT_FILE in scoped:
            raise HandoffError(f"{VOICE_SNAPSHOT_FILE} requires voice_snapshot=ready")
        return scoped
    if to_role in VOICE_ROLES and VOICE_SNAPSHOT_FILE not in scoped:
        scoped.append(VOICE_SNAPSHOT_FILE)
    return scoped


def _validate_ready_voice_snapshot(run_fd: int, status: dict) -> None:
    """Validate the frozen Voice contract without consulting the mutable registry."""
    try:
        snapshot = read_json_at(run_fd, VOICE_SNAPSHOT_FILE)
        validate_snapshot(snapshot)
    except (ContextError, VoiceError) as error:
        raise HandoffError(f"invalid Voice Snapshot: {error}") from error
    expected = {
        "voice_id": snapshot["profile_id"],
        "voice_profile_version": snapshot["profile_version"],
        "voice_snapshot": "ready",
        "voice_snapshot_sha256": snapshot["snapshot_sha256"],
    }
    if snapshot["task_id"] != status["task_id"] or any(status.get(key) != value for key, value in expected.items()):
        raise HandoffError("status.json does not match Voice Snapshot")


def _input_fresh(manifest: dict, run_dir: Path) -> tuple[bool, list[str]]:
    errors = []
    for item in manifest["allowed_inputs"]:
        try:
            path = safe_path(run_dir, item["path"], must_exist=True)
        except HandoffError:
            errors.append(f"missing input: {item['path']}")
            continue
        if not path.is_file():
            errors.append(f"input is not a file: {item['path']}")
        elif sha256_file(path) != item["sha256"]:
            errors.append(f"input hash changed: {item['path']}")
    return not errors, errors


def _load_attempt(attempt_dir: Path, run_dir: Path) -> tuple[dict, dict]:
    manifest_path = attempt_dir / "manifest.json"
    state_path = attempt_dir / "state.json"
    manifest, state = _read_json(manifest_path), _read_json(state_path)
    validate_manifest(manifest, run_dir)
    required = {"schema_version", "handoff_id", "attempt", "status", "manifest_sha256", "created_at", "updated_at"}
    missing = required - state.keys()
    if missing or state.get("schema_version") != SCHEMA_VERSION:
        raise HandoffError(f"invalid handoff state: missing={sorted(missing)}")
    if state.get("handoff_id") != manifest["handoff_id"]:
        raise HandoffError("state belongs to a different handoff")
    if state.get("manifest_sha256") != _json_hash(manifest):
        raise HandoffError("manifest hash mismatch")
    if state.get("status") not in TRANSITIONS or state.get("attempt") != manifest["attempt"]:
        raise HandoffError("invalid handoff state")
    for key in ("created_at", "updated_at"):
        if not isinstance(state[key], str):
            raise HandoffError(f"invalid state timestamp: {key}")
        try:
            datetime.fromisoformat(state[key])
        except ValueError as error:
            raise HandoffError(f"invalid state timestamp: {key}") from error
    if state["status"] in {"running", "completed", "failed"} and not isinstance(state.get("agent_ref"), str):
        raise HandoffError("state agent_ref is required after start")
    return manifest, state


def _write_state(attempt_dir: Path, state: dict, *, directory_fd: int | None = None) -> None:
    if directory_fd is None:
        atomic_write_json(attempt_dir / "state.json", state)
    else:
        _atomic_write_json_at(directory_fd, "state.json", state)


def _set_state(
    attempt_dir: Path, state: dict, target: str, *, reason: str | None = None, agent_ref: str | None = None,
) -> dict:
    if target not in TRANSITIONS.get(state["status"], set()):
        raise HandoffError(f"invalid transition {state['status']} -> {target}")
    state = dict(state)
    state["status"] = target
    state["updated_at"] = _now()
    if reason:
        state["reason"] = reason
    if agent_ref is not None:
        state["agent_ref"] = agent_ref
    _write_state(attempt_dir, state)
    return state


def _reference(manifest: dict, state: dict, attempt_dir: Path, run_dir: Path) -> dict:
    return {
        "handoff_id": manifest["handoff_id"],
        "phase": manifest["phase"],
        "to_role": manifest["to_role"],
        "attempt": manifest["attempt"],
        "status": state["status"],
        "path": attempt_dir.relative_to(run_dir).as_posix(),
        "manifest_sha256": state["manifest_sha256"],
    }


def prepare(
    run_dir: Path | str, *, to_role: str, phase: str, objective: str, decision_to_inform: str,
    inputs: list[str], write_scope: list[str], done_criteria: list[str], from_role: str = "lead",
    forbidden_inputs: list[str] | None = None, expected_outputs: list[str] | None = None,
) -> dict:
    if to_role not in ROLES - {"lead"} or from_role not in ROLES:
        raise HandoffError("to_role must be a specialist role and from_role must be known")
    _slug(phase, "phase")
    if not objective or not decision_to_inform:
        raise HandoffError("phase, objective, and decision_to_inform are required")
    expected_outputs = expected_outputs or write_scope
    input_records = []
    with _anchored_run_directory(run_dir) as (run_fd, anchored_run_dir):
        with _lock_fd(run_fd):
            status = _status(anchored_run_dir)
            current_manifest = current_state = None
            current = status.get("current_handoff")
            if isinstance(current, dict) and isinstance(current.get("path"), str):
                current_dir = safe_path(anchored_run_dir, current["path"], must_exist=True)
                current_manifest, current_state = _load_attempt(current_dir, anchored_run_dir)
                if current_state["status"] in {"prepared", "running"}:
                    raise HandoffError("current handoff must finish or become stale before preparing another")
            retry = (phase, to_role)
            stale_stages = _latest_completed_stale(anchored_run_dir)
            if stale_stages:
                earliest = stale_stages[0]["handoff"]
                if retry != (earliest["phase"], earliest["to_role"]):
                    raise HandoffError("retry the earliest stale handoff before downstream work")
            elif current_state and current_state["status"] in {"failed", "stale"}:
                if retry != (current_manifest["phase"], current_manifest["to_role"]):
                    raise HandoffError("retry the current failed or stale handoff before downstream work")
            scoped_inputs = _voice_scoped_inputs(status, to_role, inputs)
            if status.get("voice_snapshot") == "ready" and to_role in VOICE_ROLES:
                _validate_ready_voice_snapshot(run_fd, status)
            for raw in scoped_inputs:
                relative = _relative_path(raw)
                input_records.append({
                    "path": relative,
                    "sha256": _sha256_relative_file_at(run_fd, relative),
                    "required": True,
                })
            for path in write_scope + expected_outputs:
                _relative_path(path)
            if not all(_within_scope(path, write_scope) for path in expected_outputs):
                raise HandoffError("expected outputs must be inside write_scope")
            with _new_attempt_directory(run_fd, anchored_run_dir, phase, to_role) as (
                attempt,
                attempt_dir,
                attempt_fd,
            ):
                relative_attempt = attempt_dir.relative_to(anchored_run_dir).as_posix()
                manifest = {
                    "schema_version": SCHEMA_VERSION,
                    "handoff_id": f"{status['task_id']}-{phase}-{to_role}-{attempt:02d}",
                    "task_id": status["task_id"],
                    "attempt": attempt,
                    "from_role": from_role,
                    "to_role": to_role,
                    "phase": phase,
                    "objective": objective,
                    "decision_to_inform": decision_to_inform,
                    "allowed_inputs": input_records,
                    "forbidden_inputs": forbidden_inputs or [],
                    "write_scope": write_scope,
                    "expected_outputs": expected_outputs,
                    "done_criteria": done_criteria,
                    "status": "prepared",
                    "role_card": f"skills/writing-master/agents/{to_role.replace('_', '-')}.md",
                    "output_root": f"{relative_attempt}/outputs",
                    "result_path": f"{relative_attempt}/result.json",
                }
                validate_manifest(manifest, anchored_run_dir)
                _atomic_write_json_at(attempt_fd, "manifest.json", manifest)
                state = {
                    "schema_version": SCHEMA_VERSION,
                    "handoff_id": manifest["handoff_id"],
                    "attempt": attempt,
                    "status": "prepared",
                    "manifest_sha256": _json_hash(manifest),
                    "created_at": _now(),
                    "updated_at": _now(),
                }
                _write_state(attempt_dir, state, directory_fd=attempt_fd)
            status["current_handoff"] = _reference(manifest, state, attempt_dir, anchored_run_dir)
            _atomic_write_json_at(run_fd, "status.json", status)
            try:
                stable_run_dir = resolved_run_directory(run_fd)
            except RunFsError as error:
                raise HandoffError(str(error)) from error
    return {
        "manifest": manifest,
        "state": state,
        "attempt_dir": stable_run_dir / relative_attempt,
    }


def _current_attempt(run_dir: Path) -> tuple[Path, dict, dict]:
    status = _status(run_dir)
    reference = status.get("current_handoff")
    if not isinstance(reference, dict) or not isinstance(reference.get("path"), str):
        raise HandoffError("status.json has no current_handoff")
    attempt_dir = safe_path(run_dir, reference["path"], must_exist=True)
    manifest, state = _load_attempt(attempt_dir, run_dir)
    return attempt_dir, manifest, state


def _latest_completed_stale(run_dir: Path) -> list[dict]:
    """Find stale latest completed attempts without introducing workflow edges."""
    stale = []
    handoffs = run_dir / "handoffs"
    if not handoffs.is_dir():
        return stale
    for stage_dir in handoffs.iterdir():
        if not stage_dir.is_dir() or stage_dir.is_symlink():
            continue
        attempts = []
        for attempt_dir in stage_dir.glob("attempt-*"):
            suffix = attempt_dir.name.removeprefix("attempt-")
            if attempt_dir.is_dir() and suffix.isdigit():
                attempts.append((int(suffix), attempt_dir))
        if not attempts:
            continue
        completed = None
        for _, attempt_dir in sorted(attempts, reverse=True):
            if not (attempt_dir / "manifest.json").is_file() or not (attempt_dir / "state.json").is_file():
                continue
            manifest, state = _load_attempt(attempt_dir, run_dir)
            if state["status"] == "completed":
                completed = attempt_dir, manifest, state
                break
        if completed is None:
            continue
        attempt_dir, manifest, state = completed
        fresh, reasons = _input_fresh(manifest, run_dir)
        intact, integrity_reasons = _completed_integrity(manifest, state, run_dir)
        if not fresh or not intact:
            stale.append({
                "handoff": _reference(manifest, state, attempt_dir, run_dir),
                "blocking_reasons": reasons + integrity_reasons,
                "created_at": state["created_at"],
            })
    return sorted(stale, key=lambda item: item["created_at"])


def mark_running(run_dir: Path | str, agent_ref: str) -> dict:
    """Persist the host Agent reference before that Agent is spawned."""
    if not agent_ref:
        raise HandoffError("agent_ref is required")
    run_dir = Path(run_dir).resolve()
    with _lock(run_dir):
        attempt_dir, manifest, state = _current_attempt(run_dir)
        fresh, errors = _input_fresh(manifest, run_dir)
        if not fresh:
            state = _set_state(attempt_dir, state, "stale", reason="; ".join(errors))
        else:
            state = _set_state(attempt_dir, state, "running", agent_ref=agent_ref)
        status = _status(run_dir)
        status["current_handoff"] = _reference(manifest, state, attempt_dir, run_dir)
        _write_status(run_dir, status)
    return state


def recover_lost_running(run_dir: Path | str, agent_ref: str) -> dict:
    """Replace a running attempt after the host confirms its Agent is gone."""
    if not isinstance(agent_ref, str) or not agent_ref:
        raise HandoffError("agent_ref is required")
    run_dir = Path(run_dir).resolve()
    with _lock(run_dir):
        attempt_dir, manifest, state = _current_attempt(run_dir)
        if state["status"] != "running":
            raise HandoffError("only a running handoff can be recovered")
        if state.get("agent_ref") != agent_ref:
            raise HandoffError("agent_ref does not match running handoff")
        failed = _set_state(attempt_dir, state, "failed", reason="host_failure")
        status = _status(run_dir)
        status["current_handoff"] = _reference(manifest, failed, attempt_dir, run_dir)
        _write_status(run_dir, status)
    prepared = prepare(
        run_dir,
        to_role=manifest["to_role"],
        phase=manifest["phase"],
        objective=manifest["objective"],
        decision_to_inform=manifest["decision_to_inform"],
        inputs=[item["path"] for item in manifest["allowed_inputs"]],
        write_scope=manifest["write_scope"],
        done_criteria=manifest["done_criteria"],
        from_role=manifest["from_role"],
        forbidden_inputs=manifest["forbidden_inputs"],
        expected_outputs=manifest["expected_outputs"],
    )
    return {"failed": failed, "prepared": prepared}


def _atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    try:
        with source.open("rb") as source_handle, os.fdopen(fd, "wb") as destination_handle:
            for chunk in iter(lambda: source_handle.read(1024 * 1024), b""):
                destination_handle.write(chunk)
            destination_handle.flush()
            os.fsync(destination_handle.fileno())
        os.replace(temporary, destination)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _staged_output_paths(output_root: Path) -> set[str]:
    if output_root.is_symlink() or not output_root.is_dir():
        raise HandoffError("output_root must be a real directory")
    paths = set()
    for path in output_root.rglob("*"):
        relative = path.relative_to(output_root).as_posix()
        if path.is_symlink():
            raise HandoffError(f"staged output symlink: {relative}")
        if path.is_file():
            paths.add(relative)
        elif not path.is_dir():
            raise HandoffError(f"unsupported staged output: {relative}")
    return paths


def _validated_staged_outputs(result: dict, manifest: dict, run_dir: Path) -> list[dict]:
    output_root = safe_path(run_dir, manifest["output_root"], must_exist=True)
    outputs = _result_outputs(result, manifest)
    if _staged_output_paths(output_root) != {output["path"] for output in outputs}:
        raise HandoffError("staged outputs do not exactly match Result")
    for output in outputs:
        logical = output["path"]
        if not _within_scope(logical, manifest["write_scope"]):
            raise HandoffError(f"output outside write_scope: {logical}")
        source = safe_path(output_root, logical, must_exist=True)
        if not source.is_file() or source.is_symlink() or sha256_file(source) != output["sha256"]:
            raise HandoffError(f"invalid staged output: {logical}")
    return outputs


def _completed_integrity(manifest: dict, state: dict, run_dir: Path) -> tuple[bool, list[str]]:
    """Validate a historical completion without changing its recorded state."""
    try:
        try:
            result_file = safe_path(run_dir, manifest["result_path"], must_exist=True)
        except HandoffError as error:
            raise HandoffError(f"missing Result: {manifest['result_path']}") from error
        if result_file.is_symlink() or not result_file.is_file():
            raise HandoffError(f"missing Result: {manifest['result_path']}")
        result = _read_json(result_file)
        validate_result(result, manifest)
        if result["status"] != "completed":
            raise HandoffError("completed handoff requires a completed Result")
        if result["agent_ref"] != state.get("agent_ref"):
            raise HandoffError("Result agent_ref does not match completed handoff")
        outputs = _validated_staged_outputs(result, manifest, run_dir)
        for output in outputs:
            try:
                promoted = safe_path(run_dir, output["path"], must_exist=True)
            except HandoffError as error:
                raise HandoffError(f"missing promoted output: {output['path']}") from error
            if not promoted.is_file() or promoted.is_symlink():
                raise HandoffError(f"missing promoted output: {output['path']}")
            if sha256_file(promoted) != output["sha256"]:
                raise HandoffError(f"promoted output hash mismatch: {output['path']}")
    except HandoffError as error:
        return False, [str(error)]
    return True, []


def complete(run_dir: Path | str, result_path: Path | str | None = None) -> dict:
    run_dir = Path(run_dir).resolve()
    with _lock(run_dir):
        attempt_dir, manifest, state = _current_attempt(run_dir)
        if state["status"] != "running":
            raise HandoffError("only a running handoff can complete")
        fresh, errors = _input_fresh(manifest, run_dir)
        if not fresh:
            state = _set_state(attempt_dir, state, "stale", reason="; ".join(errors))
            status = _status(run_dir)
            status["current_handoff"] = _reference(manifest, state, attempt_dir, run_dir)
            _write_status(run_dir, status)
            raise HandoffError("input changed; handoff is stale")
        result = None
        try:
            canonical_result = safe_path(run_dir, manifest["result_path"])
            if result_path is None:
                result_file = safe_path(run_dir, manifest["result_path"], must_exist=True)
            else:
                result_file = safe_path(run_dir, _relative_path(str(result_path)), must_exist=True)
            result = _read_json(result_file)
            validate_result(result, manifest)
            if result["agent_ref"] != state.get("agent_ref"):
                raise HandoffError("result agent_ref does not match running handoff")
            if result_file != canonical_result:
                _atomic_copy(result_file, canonical_result)
            if result["status"] == "completed":
                outputs = _validated_staged_outputs(result, manifest, run_dir)
                output_root = safe_path(run_dir, manifest["output_root"], must_exist=True)
                for output in outputs:
                    _atomic_copy(safe_path(output_root, output["path"], must_exist=True), safe_path(run_dir, output["path"]))
                state = _set_state(attempt_dir, state, "completed")
            else:
                state = _set_state(attempt_dir, state, "failed", reason=result["failure_type"])
        except HandoffError as error:
            state = _set_state(attempt_dir, state, "failed", reason=f"output_validation: {error}")
            status = _status(run_dir)
            status["current_handoff"] = _reference(manifest, state, attempt_dir, run_dir)
            _write_status(run_dir, status)
            raise
        status = _status(run_dir)
        reference = _reference(manifest, state, attempt_dir, run_dir)
        status["current_handoff"] = reference
        if state["status"] == "completed":
            status["last_completed_handoff"] = reference
        _write_status(run_dir, status)
    return {"manifest": manifest, "state": state, "result": result}


def show(run_dir: Path | str) -> dict:
    run_dir = Path(run_dir).resolve()
    with _lock(run_dir):
        attempt_dir, manifest, state = _current_attempt(run_dir)
        fresh, errors = _input_fresh(manifest, run_dir)
        if not fresh and state["status"] in {"prepared", "running"}:
            state = _set_state(attempt_dir, state, "stale", reason="; ".join(errors))
            status = _status(run_dir)
            status["current_handoff"] = _reference(manifest, state, attempt_dir, run_dir)
            _write_status(run_dir, status)
        stale_stages = _latest_completed_stale(run_dir)
        historical_reasons = [
            f"stale {item['handoff']['phase']}/{item['handoff']['to_role']}: {reason}"
            for item in stale_stages for reason in item["blocking_reasons"]
        ]
        effective = "stale" if stale_stages or not fresh else state["status"]
        current_reasons = errors + ([state["reason"]] if state.get("reason") else [])
        return {
            "handoff": _reference(manifest, state, attempt_dir, run_dir),
            "input_fresh": fresh,
            "effective_status": effective,
            "agent_ref": state.get("agent_ref"),
            "state_reason": state.get("reason"),
            "blocking_reasons": current_reasons + historical_reasons,
            "stale_handoffs": stale_stages,
        }
