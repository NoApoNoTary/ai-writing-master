"""Task-local, immutable writing contract artifacts."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Mapping

from writing_master._runfs import RunFsError, run_directory, run_lock
from writing_master.personal_context import (
    ContextError,
    atomic_write_bytes_at,
    canonical_json_bytes,
    read_bytes_at,
)

SPEC_FILE = "spec.md"
SPEC_METADATA_FILE = "spec-metadata.json"
SPEC_SCHEMA_VERSION = 1
SPEC_FIELDS = (
    ("读者目标", "reader_goal"),
    ("交付物", "deliverable"),
    ("正文必含", "required_content"),
    ("读者可见内容", "reader_visible"),
    ("内部执行约束", "internal_constraints"),
    ("Persona / Voice", "persona_voice"),
    ("验收条件", "acceptance_criteria"),
    ("采用的失败案例规则", "failure_case_rules"),
    ("待确认项", "open_items"),
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class SpecError(ValueError):
    """Stable Run Spec contract failure."""

    def __init__(self, code: str, message: str | None = None):
        self.code = code
        super().__init__(message or code)


def _lines(value: object) -> list[str]:
    if value is None:
        return ["（未提供）"]
    if isinstance(value, str):
        return [value] if value else ["（未提供）"]
    if isinstance(value, (list, tuple)) and all(isinstance(item, str) for item in value):
        return list(value) or ["（无）"]
    raise SpecError("invalid_input", "spec field must be a string or list of strings")


def _version(value: object) -> int:
    if type(value) is not int or value < 1:
        raise SpecError("invalid_input", "version must be a positive integer")
    return value


def _expected_hash(value: object) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise SpecError("invalid_input", "expected_sha256 must be a lowercase SHA-256")
    return value


def _history_file(version: int) -> str:
    return f"spec-v{version}.md"


def render_spec(contract: Mapping[str, object], *, version: int = 1) -> str:
    if not isinstance(contract, Mapping):
        raise SpecError("invalid_input", "contract must be a mapping")
    version = _version(version)
    title = contract.get("title", "Writing Spec")
    if not isinstance(title, str) or not title.strip():
        raise SpecError("invalid_input", "title must be a non-empty string")
    lines = [f"# {title.strip()}", "", f"- spec_version: {version}", "- state: frozen", ""]
    for heading, field in SPEC_FIELDS:
        lines.extend([f"## {heading}", ""])
        lines.extend(f"- {item}" for item in _lines(contract.get(field)))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _read_optional_at(run_fd: int, name: str) -> bytes | None:
    try:
        return read_bytes_at(run_fd, name)
    except ContextError as error:
        if error.code == "not_initialized":
            return None
        raise


def _parse_metadata(raw: bytes) -> dict:
    try:
        metadata = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise SpecError("invalid_json", "invalid spec metadata") from error
    expected = {"schema_version", "current_version", "current_sha256", "versions"}
    if not isinstance(metadata, dict) or set(metadata) != expected:
        raise SpecError("schema_unsupported", "unsupported spec metadata")
    current = metadata.get("current_version")
    versions = metadata.get("versions")
    if (
        metadata.get("schema_version") != SPEC_SCHEMA_VERSION
        or type(current) is not int
        or current < 1
        or not isinstance(metadata.get("current_sha256"), str)
        or _SHA256.fullmatch(metadata["current_sha256"]) is None
        or not isinstance(versions, dict)
        or str(current) not in versions
    ):
        raise SpecError("schema_unsupported", "unsupported spec metadata")
    for key, item in versions.items():
        if (
            not isinstance(key, str)
            or not key.isdigit()
            or int(key) < 1
            or not isinstance(item, dict)
            or set(item) != {"path", "sha256"}
            or item.get("path") != _history_file(int(key))
            or not isinstance(item.get("sha256"), str)
            or _SHA256.fullmatch(item["sha256"]) is None
        ):
            raise SpecError("schema_unsupported", "unsupported spec metadata")
    if versions[str(current)]["sha256"] != metadata["current_sha256"]:
        raise SpecError("hash_mismatch", "current spec metadata is inconsistent")
    return metadata


def _result(metadata: dict, version: int | None = None) -> dict:
    selected = metadata["current_version"] if version is None else version
    item = metadata["versions"].get(str(selected))
    if item is None:
        raise SpecError("not_found", f"spec version is not recorded: {selected}")
    return {
        "path": SPEC_FILE if selected == metadata["current_version"] else item["path"],
        "version": selected,
        "sha256": item["sha256"],
        "state": "frozen",
    }


def _metadata_and_history_at(run_fd: int) -> tuple[dict, dict[int, bytes]]:
    raw_metadata = _read_optional_at(run_fd, SPEC_METADATA_FILE)
    if raw_metadata is None:
        raise SpecError("not_initialized", "spec metadata is missing")
    metadata = _parse_metadata(raw_metadata)
    history: dict[int, bytes] = {}
    for key, item in metadata["versions"].items():
        selected = int(key)
        raw = _read_optional_at(run_fd, item["path"])
        if raw is None:
            raise SpecError("not_initialized", f"spec history is missing: {item['path']}")
        actual = hashlib.sha256(raw).hexdigest()
        if actual != item["sha256"]:
            raise SpecError("hash_mismatch", f"spec history hash changed: {item['path']}")
        history[selected] = raw
    return metadata, history


def _verify_at(
    run_fd: int, *, expected_sha256: str | None = None, version: int | None = None,
) -> tuple[dict, dict]:
    if version is not None:
        version = _version(version)
    metadata, history = _metadata_and_history_at(run_fd)
    current = _read_optional_at(run_fd, SPEC_FILE)
    if current is None:
        raise SpecError("not_initialized", "spec.md is missing")
    current_version = metadata["current_version"]
    if current != history[current_version]:
        raise SpecError("hash_mismatch", "spec.md does not match current history")
    result = _result(metadata, version)
    if expected_sha256 is not None and result["sha256"] != _expected_hash(expected_sha256):
        raise SpecError("hash_mismatch", "spec hash does not match expected_sha256")
    return metadata, result


def _translate(error: RunFsError | ContextError) -> SpecError:
    return SpecError(error.code, str(error))


def save_spec(run_dir: Path | str, contract: Mapping[str, object], *, version: int = 1) -> dict:
    version = _version(version)
    raw = render_spec(contract, version=version).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    try:
        with run_directory(run_dir) as (run_fd, _):
            with run_lock(run_fd):
                raw_metadata = _read_optional_at(run_fd, SPEC_METADATA_FILE)
                if raw_metadata is None:
                    if version != 1:
                        raise SpecError("conflict", "initial spec version must be 1")
                    history_name = _history_file(version)
                    existing_history = _read_optional_at(run_fd, history_name)
                    existing_current = _read_optional_at(run_fd, SPEC_FILE)
                    for name, existing in (
                        (history_name, existing_history),
                        (SPEC_FILE, existing_current),
                    ):
                        if existing is not None and existing != raw:
                            raise SpecError("conflict", f"unmanaged spec artifact has different content: {name}")
                    metadata = {
                        "schema_version": SPEC_SCHEMA_VERSION,
                        "current_version": version,
                        "current_sha256": digest,
                        "versions": {str(version): {"path": history_name, "sha256": digest}},
                    }
                    if existing_history is None:
                        atomic_write_bytes_at(run_fd, history_name, raw)
                    if existing_current is None:
                        atomic_write_bytes_at(run_fd, SPEC_FILE, raw)
                    atomic_write_bytes_at(run_fd, SPEC_METADATA_FILE, canonical_json_bytes(metadata))
                    return _result(metadata)

                metadata, history = _metadata_and_history_at(run_fd)
                existing = metadata["versions"].get(str(version))
                if existing is not None:
                    current = _read_optional_at(run_fd, SPEC_FILE)
                    if current != history[metadata["current_version"]]:
                        raise SpecError("hash_mismatch", "spec.md does not match current history")
                    if existing["sha256"] != digest:
                        raise SpecError("conflict", f"spec version {version} already has different content")
                    return _result(metadata, version)
                if version != metadata["current_version"] + 1:
                    raise SpecError("conflict", "new spec version must follow the current version")

                history_name = _history_file(version)
                existing_history = _read_optional_at(run_fd, history_name)
                if existing_history is not None and existing_history != raw:
                    raise SpecError("conflict", f"spec history already exists: {history_name}")
                current = _read_optional_at(run_fd, SPEC_FILE)
                if current not in {history[metadata["current_version"]], raw}:
                    raise SpecError("hash_mismatch", "spec.md is neither current nor the requested next version")
                if existing_history is None:
                    atomic_write_bytes_at(run_fd, history_name, raw)
                if current != raw:
                    atomic_write_bytes_at(run_fd, SPEC_FILE, raw)
                updated = {
                    **metadata,
                    "current_version": version,
                    "current_sha256": digest,
                    "versions": {
                        **metadata["versions"],
                        str(version): {"path": history_name, "sha256": digest},
                    },
                }
                atomic_write_bytes_at(run_fd, SPEC_METADATA_FILE, canonical_json_bytes(updated))
                return _result(updated)
    except (RunFsError, ContextError) as error:
        raise _translate(error) from error


def verify_spec(
    run_dir: Path | str, *, expected_sha256: str | None = None, version: int | None = None,
) -> dict:
    try:
        with run_directory(run_dir) as (run_fd, _):
            with run_lock(run_fd):
                _, result = _verify_at(
                    run_fd,
                    expected_sha256=expected_sha256,
                    version=version,
                )
                return result
    except (RunFsError, ContextError) as error:
        raise _translate(error) from error


def spec_sha256(run_dir: Path | str) -> str:
    return verify_spec(run_dir)["sha256"]
