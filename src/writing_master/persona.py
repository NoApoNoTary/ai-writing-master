"""Task-local snapshots for selected Persona Skills."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat

from writing_master._runfs import (
    RunFsError,
    resolved_descriptor_path,
    run_directory,
    run_lock,
)
from writing_master.personal_context import (
    ContextError,
    atomic_write_bytes_at,
    atomic_write_json_at,
    read_bytes_at,
    read_json_at,
)
from writing_master.persona_templates import (
    TemplateSourceError,
    external_source_path,
    load_builtin,
    source_identity,
)


PERSONA_SKILL_FILE = "persona-skill.md"
PERSONA_BRIEF_FILE = "persona-brief.md"
MODES = {"author", "reference"}
CONTENT_TYPES = {"release", "analysis", "review", "opinion", "tutorial", "story"}
BACKGROUND_MODES = {"default", "project", "none"}
STATUS_FIELDS = {
    "persona_mode",
    "persona_snapshot",
    "persona_source_path",
    "persona_source_version",
    "persona_source_sha256",
    "persona_brief_sha256",
}
_PROVENANCE_FIELDS = {
    "source_input",
    "source_path",
    "source_version",
    "source_sha256",
    "mode",
    "content_type",
    "background_mode",
    "brief_sha256",
}
_HEADER = b"<!-- writing-master-persona\n"
_HEADER_END = b"\n-->\n\n"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class PersonaError(ValueError):
    """Stable Persona runtime contract failure."""

    def __init__(self, code: str, message: str | None = None):
        self.code = code
        super().__init__(message or code)


def _source_input(source: Path | str) -> str:
    if not isinstance(source, (str, os.PathLike)):
        raise PersonaError("invalid_input", "persona source must be a non-empty path")
    try:
        value = os.fspath(source)
    except (TypeError, ValueError) as error:
        raise PersonaError("invalid_input", "persona source must be a text path") from error
    if not isinstance(value, str) or not value:
        raise PersonaError("invalid_input", "persona source must be a text path")
    if "\x00" in value or "\n" in value or "\r" in value:
        raise PersonaError("path_escape", "Persona Skill path is unsafe")
    return value


def _read_regular_utf8(
    path: Path, *, label: str, include_path: bool = False
) -> bytes | tuple[bytes, str]:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        descriptor = os.open(path, flags)
    except FileNotFoundError as error:
        raise PersonaError("not_initialized", f"missing {label}: {path}") from error
    except (OSError, ValueError) as error:
        raise PersonaError("path_escape", f"unsafe {label}: {path}") from error
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise PersonaError("path_escape", f"{label} must be a regular file")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = None
            value = handle.read()
            if include_path:
                try:
                    source_path = str(resolved_descriptor_path(handle.fileno()))
                except RunFsError as error:
                    raise PersonaError(error.code, f"cannot resolve {label}: {path}") from error
    except PersonaError:
        raise
    except OSError as error:
        raise PersonaError("path_escape", f"cannot read {label}: {path}") from error
    finally:
        if descriptor is not None:
            os.close(descriptor)
    try:
        value.decode("utf-8")
    except UnicodeDecodeError as error:
        raise PersonaError("invalid_input", f"{label} must be UTF-8") from error
    return (value, source_path) if include_path else value


def _load_source(source: Path | str) -> tuple[str, str, bytes]:
    source_input = _source_input(source)
    try:
        builtin = load_builtin(source)
    except TemplateSourceError as error:
        raise PersonaError(error.code, str(error)) from error
    if builtin is not None:
        source_path, value = builtin
        if not value:
            raise PersonaError("invalid_input", "Persona Skill must not be empty")
        try:
            value.decode("utf-8")
        except UnicodeDecodeError as error:
            raise PersonaError("invalid_input", "Persona Skill must be UTF-8") from error
        return source_input, source_path, value
    try:
        path = external_source_path(source)
    except (OSError, RuntimeError, ValueError) as error:
        raise PersonaError("path_escape", f"unsafe Persona Skill: {source_input}") from error
    try:
        if path.is_dir():
            path = path / "SKILL.md"
    except (OSError, RuntimeError, ValueError) as error:
        raise PersonaError("path_escape", f"unsafe Persona Skill: {source_input}") from error
    value, resolved = _read_regular_utf8(path, label="Persona Skill", include_path=True)
    if not value:
        raise PersonaError("invalid_input", "Persona Skill must not be empty")
    return source_input, resolved, value


def _selector_identity(
    source: Path | str, *, check_ambiguity: bool = True
) -> tuple[str, str]:
    try:
        return source_identity(source, check_ambiguity=check_ambiguity)
    except TemplateSourceError as error:
        raise PersonaError(error.code, str(error)) from error


def _provenance_identity(provenance: dict) -> tuple[str, str]:
    source_path = provenance["source_path"]
    if source_path.startswith("builtin:"):
        return "builtin", source_path.removeprefix("builtin:")
    source_input = provenance["source_input"]
    try:
        kind, value = source_identity(source_input, check_ambiguity=False)
    except TemplateSourceError:
        kind, value = "external", source_input
    if kind == "builtin" and source_path.endswith(
        f"/persona_templates/{value}/SKILL.md"
    ):
        return kind, value
    return "external", source_input


def _matches_request(
    provenance: dict,
    requested: dict,
    selector_identity: tuple[str, str],
    source_version: str | None,
) -> bool:
    return (
        _provenance_identity(provenance) == selector_identity
        and all(provenance[key] == value for key, value in requested.items())
        and (source_version is None or provenance["source_version"] == source_version)
    )


def _version_scalar(raw: str) -> str | None:
    if raw.startswith("'"):
        match = re.fullmatch(r"'((?:[^']|'')*)'\s*(?:#.*)?", raw)
        value = match.group(1).replace("''", "'") if match else ""
    elif raw.startswith('"'):
        try:
            value, end = json.JSONDecoder().raw_decode(raw)
        except (json.JSONDecodeError, ValueError):
            return None
        rest = raw[end:].strip()
        if not isinstance(value, str) or (rest and not rest.startswith("#")):
            return None
    else:
        value = re.split(r"\s+#", raw, maxsplit=1)[0].strip()
    return None if value in {"", "null", "~"} else value


def _frontmatter_version(source: bytes) -> str | None:
    """Read only a closed, top-level frontmatter version value."""
    lines = source.decode("utf-8").splitlines()
    if not lines or lines[0].lstrip("\ufeff").strip() != "---":
        return None
    try:
        end = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration:
        return None
    for line in lines[1:end]:
        match = re.fullmatch(r"version\s*:\s*(.*?)\s*", line)
        if not match or not match.group(1):
            continue
        return _version_scalar(match.group(1))
    return None


def _source_version(source: bytes, source_sha256: str, explicit: str | None) -> str:
    detected = _frontmatter_version(source)
    if detected is not None:
        if explicit is not None and explicit != detected:
            raise PersonaError("invalid_input", "source_version does not match Persona Skill frontmatter")
        return detected
    return explicit or source_sha256


def _load_brief(brief: Path | str) -> bytes:
    if isinstance(brief, str):
        value = brief.encode("utf-8")
    elif isinstance(brief, os.PathLike):
        value = _read_regular_utf8(Path(brief).expanduser(), label="Persona Brief")
    else:
        raise PersonaError("invalid_input", "brief must be UTF-8 text or a path")
    if not value.strip():
        raise PersonaError("invalid_input", "Persona Brief must not be empty")
    return value


def _validate_provenance(value: object) -> dict:
    if not isinstance(value, dict) or set(value) != _PROVENANCE_FIELDS:
        raise PersonaError("schema_unsupported", "unsupported Persona Brief provenance")
    for field in ("source_input", "source_path"):
        if not isinstance(value.get(field), str) or not value[field]:
            raise PersonaError("schema_unsupported", f"Persona provenance {field} is required")
    if not isinstance(value.get("source_version"), str) or not value["source_version"]:
        raise PersonaError("schema_unsupported", "Persona source_version is required")
    if value.get("mode") not in MODES:
        raise PersonaError("schema_unsupported", "Persona mode is invalid")
    if value.get("content_type") not in CONTENT_TYPES:
        raise PersonaError("schema_unsupported", "Persona content_type is invalid")
    if value.get("background_mode") not in BACKGROUND_MODES:
        raise PersonaError("schema_unsupported", "Persona background_mode is invalid")
    for field in ("source_sha256", "brief_sha256"):
        if not isinstance(value.get(field), str) or _SHA256.fullmatch(value[field]) is None:
            raise PersonaError("schema_unsupported", f"Persona provenance {field} is invalid")
    return value


def _brief_document(body: bytes, provenance: dict) -> bytes:
    header = json.dumps(
        provenance,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _HEADER + header + _HEADER_END + body


def _reject_json_constant(value: str) -> None:
    raise ValueError(value)


def _parse_brief_document(value: bytes) -> tuple[dict, bytes]:
    if not value.startswith(_HEADER):
        raise PersonaError("schema_unsupported", "Persona Brief provenance header is missing")
    try:
        header, body = value[len(_HEADER):].split(_HEADER_END, 1)
        provenance = json.loads(header.decode("utf-8"), parse_constant=_reject_json_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise PersonaError("schema_unsupported", "Persona Brief provenance header is invalid") from error
    provenance = _validate_provenance(provenance)
    if hashlib.sha256(body).hexdigest() != provenance["brief_sha256"]:
        raise PersonaError("hash_mismatch", "Persona Brief body hash does not match")
    return provenance, body


def _status_at(run_fd: int) -> dict:
    try:
        status = read_json_at(run_fd, "status.json")
    except ContextError as error:
        raise PersonaError(error.code, str(error)) from error
    if not isinstance(status.get("task_id"), str) or not status["task_id"]:
        raise PersonaError("unknown_id", "run directory has no task_id")
    return status


def _status_values(provenance: dict, brief_sha256: str) -> dict:
    return {
        "persona_mode": provenance["mode"],
        "persona_snapshot": "ready",
        "persona_source_path": provenance["source_path"],
        "persona_source_version": provenance["source_version"],
        "persona_source_sha256": provenance["source_sha256"],
        "persona_brief_sha256": brief_sha256,
    }


def _result(status: dict, provenance: dict) -> dict:
    return {
        "task_id": status["task_id"],
        "persona_mode": provenance["mode"],
        "persona_snapshot": "ready",
        **provenance,
        "persona_brief_sha256": status["persona_brief_sha256"],
        "verified": True,
    }


def _verify_ready_at(run_fd: int, status: dict) -> tuple[dict, bytes]:
    if status.get("persona_snapshot") != "ready" or status.get("persona_mode") not in MODES:
        raise PersonaError("snapshot_missing", "Persona Snapshot is not ready")
    try:
        source = read_bytes_at(run_fd, PERSONA_SKILL_FILE)
        brief = read_bytes_at(run_fd, PERSONA_BRIEF_FILE)
    except ContextError as error:
        raise PersonaError(error.code, str(error)) from error
    provenance, _ = _parse_brief_document(brief)
    source_sha256 = hashlib.sha256(source).hexdigest()
    brief_sha256 = hashlib.sha256(brief).hexdigest()
    if source_sha256 != provenance["source_sha256"]:
        raise PersonaError("hash_mismatch", "task Persona Skill has changed")
    expected = _status_values(provenance, brief_sha256)
    if any(status.get(key) != value for key, value in expected.items()):
        raise PersonaError("hash_mismatch", "status.json does not match task Persona files")
    return provenance, brief


def verify_task_files_at(run_fd: int, status: dict) -> dict:
    """Verify frozen Persona files through an already anchored run directory."""
    provenance, _ = _verify_ready_at(run_fd, status)
    return provenance


def _optional_task_file_at(run_fd: int, name: str) -> bytes | None:
    try:
        return read_bytes_at(run_fd, name)
    except ContextError as error:
        if error.code == "not_initialized":
            return None
        raise PersonaError(error.code, str(error)) from error


def _persona_files_present(run_fd: int) -> bool:
    return any(
        _optional_task_file_at(run_fd, name) is not None
        for name in (PERSONA_SKILL_FILE, PERSONA_BRIEF_FILE)
    )


def _publish_task_files_at(run_fd: int, source: bytes, brief: bytes) -> None:
    for name, expected in ((PERSONA_SKILL_FILE, source), (PERSONA_BRIEF_FILE, brief)):
        existing = _optional_task_file_at(run_fd, name)
        if existing is not None and existing != expected:
            raise PersonaError("snapshot_conflict", f"task {name} conflicts with requested Persona")
        if existing is None:
            atomic_write_bytes_at(run_fd, name, expected)


def _recover_published_snapshot(
    run_fd: int,
    status: dict,
    requested: dict,
    selector_identity: tuple[str, str],
    source_version: str | None,
) -> tuple[dict, bytes] | None:
    source = _optional_task_file_at(run_fd, PERSONA_SKILL_FILE)
    brief = _optional_task_file_at(run_fd, PERSONA_BRIEF_FILE)
    if source is None and brief is None:
        return None
    if source is None or brief is None:
        raise PersonaError("snapshot_conflict", "partial task Persona files exist")
    provenance, _ = _parse_brief_document(brief)
    if hashlib.sha256(source).hexdigest() != provenance["source_sha256"]:
        raise PersonaError("hash_mismatch", "task Persona Skill has changed")
    if not _matches_request(provenance, requested, selector_identity, source_version):
        raise PersonaError("snapshot_conflict", "task already owns a different Persona Snapshot")
    _assert_pending_compatible(status, provenance, hashlib.sha256(brief).hexdigest())
    return provenance, brief


def _none_result(run_fd: int, status: dict) -> dict:
    if _persona_files_present(run_fd):
        raise PersonaError("snapshot_conflict", "Persona files exist without ready task status")
    present = STATUS_FIELDS.intersection(status)
    if not present:
        return {
            "task_id": status["task_id"],
            "persona_mode": "none",
            "persona_snapshot": "none",
            "verified": True,
        }
    if status.get("persona_mode") == "none" and status.get("persona_snapshot") == "none" and all(
        status.get(field) is None for field in STATUS_FIELDS - {"persona_mode", "persona_snapshot"}
    ):
        return {
            "task_id": status["task_id"],
            "persona_mode": "none",
            "persona_snapshot": "none",
            "verified": True,
        }
    raise PersonaError("snapshot_missing", "Persona Snapshot is required by task status")


def _assert_pending_compatible(status: dict, provenance: dict, brief_sha256: str) -> None:
    state = status.get("persona_snapshot")
    if state is None:
        if any(status.get(field) is not None for field in STATUS_FIELDS.intersection(status)):
            raise PersonaError("snapshot_conflict", "task has conflicting partial Persona status")
        return
    if state == "none":
        if status.get("persona_mode") not in {None, "none"} or any(
            status.get(field) is not None
            for field in STATUS_FIELDS - {"persona_mode", "persona_snapshot"}
        ):
            raise PersonaError("snapshot_conflict", "task has conflicting none Persona status")
        return
    if state != "pending":
        raise PersonaError("snapshot_conflict", "task Persona state cannot adopt a Snapshot")
    expected = _status_values(provenance, brief_sha256)
    for field, value in expected.items():
        if field == "persona_snapshot":
            continue
        current = status.get(field)
        if current is not None and current != value:
            raise PersonaError("snapshot_conflict", "pending Persona status conflicts with requested Snapshot")


class PersonaStore:
    def create_snapshot(
        self,
        run_dir: Path | str,
        source: Path | str,
        brief: Path | str,
        *,
        mode: str,
        content_type: str,
        background_mode: str,
        source_version: str | None = None,
    ) -> dict:
        if mode not in MODES:
            raise PersonaError("invalid_input", "unsupported Persona mode")
        if content_type not in CONTENT_TYPES:
            raise PersonaError("invalid_input", "unsupported Persona content_type")
        if background_mode not in BACKGROUND_MODES:
            raise PersonaError("invalid_input", "unsupported Persona background mode")
        if source_version is not None and (
            not isinstance(source_version, str) or not source_version.strip()
        ):
            raise PersonaError("invalid_input", "source_version must be null or non-empty")
        if source_version is not None:
            source_version = source_version.strip()
        source_input = _source_input(source)
        body = _load_brief(brief)
        requested = {
            "mode": mode,
            "content_type": content_type,
            "background_mode": background_mode,
            "brief_sha256": hashlib.sha256(body).hexdigest(),
        }
        try:
            with run_directory(run_dir) as (run_fd, _):
                with run_lock(run_fd):
                    status = _status_at(run_fd)
                    if status.get("persona_snapshot") == "ready":
                        provenance, _ = _verify_ready_at(run_fd, status)
                        selector_identity = _selector_identity(source, check_ambiguity=False)
                        if not _matches_request(
                            provenance, requested, selector_identity, source_version
                        ):
                            raise PersonaError("snapshot_conflict", "task already owns a different Persona Snapshot")
                        return _result(status, provenance)

                    recovered = _recover_published_snapshot(
                        run_fd,
                        status,
                        requested,
                        _selector_identity(source, check_ambiguity=False),
                        source_version,
                    )
                    if recovered is not None:
                        provenance, persona_brief = recovered
                        persona_brief_sha256 = hashlib.sha256(persona_brief).hexdigest()
                        updated = {**status, **_status_values(provenance, persona_brief_sha256)}
                        atomic_write_json_at(run_fd, "status.json", updated)
                        return _result(updated, provenance)

                    selector_identity = _selector_identity(source)
                    source_input, source_path, source_bytes = _load_source(source)
                    source_sha256 = hashlib.sha256(source_bytes).hexdigest()
                    provenance = {
                        "source_input": source_input,
                        "source_path": source_path,
                        "source_version": _source_version(source_bytes, source_sha256, source_version),
                        "source_sha256": source_sha256,
                        "mode": mode,
                        "content_type": content_type,
                        "background_mode": background_mode,
                        "brief_sha256": requested["brief_sha256"],
                    }
                    persona_brief = _brief_document(body, provenance)
                    persona_brief_sha256 = hashlib.sha256(persona_brief).hexdigest()
                    _assert_pending_compatible(status, provenance, persona_brief_sha256)
                    _publish_task_files_at(run_fd, source_bytes, persona_brief)
                    updated = {**status, **_status_values(provenance, persona_brief_sha256)}
                    atomic_write_json_at(run_fd, "status.json", updated)
                    return _result(updated, provenance)
        except RunFsError as error:
            raise PersonaError(error.code, str(error)) from error
        except ContextError as error:
            raise PersonaError(error.code, str(error)) from error
        except OSError as error:
            raise PersonaError("io_error", "cannot write task Persona files") from error

    def verify_run(self, run_dir: Path | str) -> dict:
        try:
            with run_directory(run_dir) as (run_fd, _):
                with run_lock(run_fd):
                    status = _status_at(run_fd)
                    if status.get("persona_snapshot") != "ready":
                        return _none_result(run_fd, status)
                    provenance, _ = _verify_ready_at(run_fd, status)
                    return _result(status, provenance)
        except RunFsError as error:
            raise PersonaError(error.code, str(error)) from error
        except ContextError as error:
            raise PersonaError(error.code, str(error)) from error
        except OSError as error:
            raise PersonaError("path_escape", "cannot verify task Persona files") from error

    def read_task_brief(self, run_dir: Path | str) -> str | None:
        try:
            with run_directory(run_dir) as (run_fd, _):
                with run_lock(run_fd):
                    status = _status_at(run_fd)
                    if status.get("persona_snapshot") != "ready":
                        _none_result(run_fd, status)
                        return None
                    _, brief = _verify_ready_at(run_fd, status)
                    try:
                        return brief.decode("utf-8")
                    except UnicodeDecodeError as error:
                        raise PersonaError("invalid_input", "task Persona Brief must be UTF-8") from error
        except RunFsError as error:
            raise PersonaError(error.code, str(error)) from error
        except ContextError as error:
            raise PersonaError(error.code, str(error)) from error
        except OSError as error:
            raise PersonaError("path_escape", "cannot read task Persona Brief") from error
