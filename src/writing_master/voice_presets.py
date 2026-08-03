"""Task-scoped Voice Preset registry and immutable snapshots."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from writing_master._runfs import RunFsError, run_directory, run_lock
from writing_master.personal_context import (
    ContextError,
    atomic_write_json_at,
    canonical_sha256,
    publish_json_once_at,
    read_json_at,
)


SCHEMA_VERSION = 1
SNAPSHOT_FILE = "voice-profile-snapshot.json"
DEFAULT_VOICE_ID = "natural-default"
PRESERVE = [
    "facts",
    "evidence_boundaries",
    "core_thesis",
    "author_position",
    "real_experiences",
]
VOICE_DIMENSIONS = (
    "register",
    "sentence_rhythm",
    "paragraph_shape",
    "pacing",
    "opening",
    "transitions",
    "certainty",
    "humor",
    "analogy",
    "vocabulary",
)
SELECTION_SOURCES = {"default", "request", "content_contract"}
VOICE_STATUS_FIELDS = (
    "voice_id",
    "voice_profile_version",
    "voice_snapshot",
    "voice_snapshot_sha256",
    "voice_selection_source",
)
_SHA256 = re.compile(r"[0-9a-f]{64}")
_RFC3339 = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


class VoiceError(ValueError):
    """Stable Voice Preset contract failure."""

    def __init__(self, code: str, message: str | None = None, *, available: list[dict] | None = None):
        self.code = code
        self.available = available
        super().__init__(message or code)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _valid_rfc3339(value: object) -> bool:
    if not isinstance(value, str) or not _RFC3339.fullmatch(value):
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _reject_json_constant(value: str) -> None:
    raise ValueError(value)


def _nonempty_strings(value: object, field: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        raise VoiceError("schema_unsupported", f"{field} must be a list of strings")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise VoiceError("schema_unsupported", f"{field} must contain non-empty strings")
    if len(value) != len(set(value)):
        raise VoiceError("schema_unsupported", f"{field} contains duplicates")
    return value


def validate_profile(profile: dict) -> None:
    required = {
        "schema_version",
        "id",
        "version",
        "label",
        "description",
        "best_for",
        "scope",
        "voice",
        "avoid",
        "preserve",
        "examples",
    }
    if not isinstance(profile, dict) or set(profile) != required:
        raise VoiceError("schema_unsupported", "unsupported Voice Profile fields")
    if profile.get("schema_version") != SCHEMA_VERSION:
        raise VoiceError("schema_unsupported", "unsupported Voice Profile schema version")
    if not isinstance(profile.get("id"), str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", profile["id"]):
        raise VoiceError("schema_unsupported", "Voice Profile id must be a stable slug")
    if type(profile.get("version")) is not int or profile["version"] < 1:
        raise VoiceError("schema_unsupported", "Voice Profile version must be a positive integer")
    for field in ("label", "description"):
        if not isinstance(profile.get(field), str) or not profile[field].strip():
            raise VoiceError("schema_unsupported", f"Voice Profile {field} is required")
    _nonempty_strings(profile.get("best_for"), "best_for")
    if profile.get("scope") != "expression_only":
        raise VoiceError("schema_unsupported", "Voice Profile scope must be expression_only")
    voice = profile.get("voice")
    if not isinstance(voice, dict) or set(voice) != set(VOICE_DIMENSIONS):
        raise VoiceError("schema_unsupported", "Voice Profile voice dimensions are invalid")
    allow_empty = profile["id"] == DEFAULT_VOICE_ID
    for dimension in VOICE_DIMENSIONS:
        _nonempty_strings(voice[dimension], f"voice.{dimension}", allow_empty=allow_empty)
    _nonempty_strings(profile.get("avoid"), "avoid", allow_empty=allow_empty)
    if profile.get("preserve") != PRESERVE:
        raise VoiceError("schema_unsupported", "Voice Profile preserve contract is fixed")
    if not isinstance(profile.get("examples"), list):
        raise VoiceError("schema_unsupported", "Voice Profile examples must be a list")
    if len(profile["examples"]) > 10:
        raise VoiceError("schema_unsupported", "Voice Profile examples must stay compact")
    for example in profile["examples"]:
        paired = (
            isinstance(example, dict)
            and set(example) == {"rule", "input", "output"}
            and all(isinstance(example[key], str) and example[key].strip() for key in example)
            and all(len(example[key]) <= 500 for key in example)
        )
        rendered = (
            isinstance(example, dict)
            and set(example) == {"rules", "text"}
            and isinstance(example.get("rules"), list)
            and bool(example["rules"])
            and all(isinstance(rule, str) and rule.strip() for rule in example["rules"])
            and isinstance(example.get("text"), str)
            and bool(example["text"].strip())
            and len(example["text"]) <= 500
        )
        if not paired and not rendered:
            raise VoiceError("schema_unsupported", "Voice Profile examples must be compact synthetic examples with rule references")
    if allow_empty and (
        any(voice[dimension] for dimension in VOICE_DIMENSIONS)
        or profile["avoid"]
        or profile["examples"]
    ):
        raise VoiceError("schema_unsupported", "natural-default must not add Voice overrides")


def validate_registry(registry: dict) -> None:
    if (
        not isinstance(registry, dict)
        or set(registry) != {"schema_version", "default_id", "profiles"}
        or registry.get("schema_version") != SCHEMA_VERSION
        or not isinstance(registry.get("profiles"), list)
        or not registry["profiles"]
    ):
        raise VoiceError("registry_invalid", "unsupported Voice Registry")
    try:
        for profile in registry["profiles"]:
            validate_profile(profile)
    except VoiceError as error:
        raise VoiceError("registry_invalid", str(error)) from error
    ids = [profile["id"] for profile in registry["profiles"]]
    labels = [profile["label"].casefold() for profile in registry["profiles"]]
    if len(ids) != len(set(ids)) or len(labels) != len(set(labels)):
        raise VoiceError("registry_invalid", "Voice Registry ids and labels must be unique")
    if registry.get("default_id") != DEFAULT_VOICE_ID or ids.count(DEFAULT_VOICE_ID) != 1:
        raise VoiceError("registry_invalid", "Voice Registry must contain exactly one natural-default")


def validate_snapshot(snapshot: dict) -> None:
    required = {
        "schema_version",
        "task_id",
        "created_at",
        "selection_source",
        "profile_id",
        "profile_version",
        "profile_sha256",
        "profile",
        "snapshot_sha256",
    }
    if not isinstance(snapshot, dict) or set(snapshot) != required or snapshot.get("schema_version") != SCHEMA_VERSION:
        raise VoiceError("schema_unsupported", "unsupported Voice Snapshot")
    if not isinstance(snapshot.get("task_id"), str) or not snapshot["task_id"]:
        raise VoiceError("schema_unsupported", "Voice Snapshot task_id is required")
    if snapshot.get("selection_source") not in SELECTION_SOURCES:
        raise VoiceError("schema_unsupported", "Voice Snapshot selection_source is invalid")
    if not _valid_rfc3339(snapshot.get("created_at")):
        raise VoiceError("schema_unsupported", "Voice Snapshot created_at is invalid")
    validate_profile(snapshot.get("profile"))
    profile = snapshot["profile"]
    if snapshot.get("profile_id") != profile["id"] or snapshot.get("profile_version") != profile["version"]:
        raise VoiceError("hash_mismatch", "Voice Snapshot profile identity does not match")
    if not isinstance(snapshot.get("profile_sha256"), str) or not _SHA256.fullmatch(snapshot["profile_sha256"]):
        raise VoiceError("schema_unsupported", "Voice Snapshot profile_sha256 is invalid")
    if snapshot["profile_sha256"] != canonical_sha256(profile):
        raise VoiceError("hash_mismatch", "Voice Snapshot profile hash does not match")
    if not isinstance(snapshot.get("snapshot_sha256"), str) or not _SHA256.fullmatch(snapshot["snapshot_sha256"]):
        raise VoiceError("schema_unsupported", "Voice Snapshot hash is invalid")
    payload = {key: value for key, value in snapshot.items() if key != "snapshot_sha256"}
    if snapshot["snapshot_sha256"] != canonical_sha256(payload):
        raise VoiceError("hash_mismatch", "Voice Snapshot hash does not match")


class VoicePresetStore:
    def __init__(self, registry_path: Path | str | None = None):
        self.registry_path = Path(registry_path) if registry_path else Path(__file__).with_name("voice_profiles") / "registry.json"

    def read_registry(self) -> dict:
        try:
            value = json.loads(
                self.registry_path.read_text(encoding="utf-8"),
                parse_constant=_reject_json_constant,
            )
        except OSError as error:
            raise VoiceError("registry_unavailable", "Voice Registry is unavailable") from error
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as error:
            raise VoiceError("registry_invalid", "Voice Registry JSON is invalid") from error
        validate_registry(value)
        return value

    @staticmethod
    def summaries(registry: dict) -> list[dict]:
        return [
            {
                "number": index,
                "id": profile["id"],
                "version": profile["version"],
                "label": profile["label"],
                "description": profile["description"],
                "best_for": profile["best_for"],
                "default": profile["id"] == registry["default_id"],
            }
            for index, profile in enumerate(registry["profiles"], 1)
        ]

    def list_profiles(self) -> dict:
        registry = self.read_registry()
        return {"default_id": registry["default_id"], "profiles": self.summaries(registry)}

    def resolve(self, selector: str | int | None, registry: dict | None = None) -> dict:
        registry = registry or self.read_registry()
        profiles = registry["profiles"]
        if selector is None or (isinstance(selector, str) and not selector.strip()):
            selector = registry["default_id"]
        if type(selector) is int or (isinstance(selector, str) and selector.strip().isdigit()):
            number = int(selector)
            if 1 <= number <= len(profiles):
                return profiles[number - 1]
        elif isinstance(selector, str):
            normalized = selector.strip().casefold()
            matches = [profile for profile in profiles if normalized in {profile["id"].casefold(), profile["label"].casefold()}]
            if len(matches) == 1:
                return matches[0]
        raise VoiceError(
            "unknown_voice",
            f"unknown or unavailable Voice Preset: {selector}",
            available=self.summaries(registry),
        )

    @staticmethod
    def _task_id_at(run_fd: int) -> str:
        try:
            status = read_json_at(run_fd, "status.json")
        except ContextError as error:
            raise VoiceError(error.code, str(error)) from error
        task_id = status.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            raise VoiceError("unknown_id", "run directory has no task_id")
        return task_id

    @staticmethod
    def _read_snapshot_at(run_fd: int) -> dict | None:
        try:
            snapshot = read_json_at(run_fd, SNAPSHOT_FILE)
        except ContextError as error:
            if error.code == "not_initialized":
                return None
            raise VoiceError(error.code, str(error)) from error
        validate_snapshot(snapshot)
        return snapshot

    @staticmethod
    def _write_status_at(run_fd: int, status: dict, snapshot: dict | None, state: str) -> dict:
        updated = dict(status)
        if snapshot is None:
            updated.update({
                "voice_id": DEFAULT_VOICE_ID if state == "unavailable" else "legacy-natural",
                "voice_profile_version": None,
                "voice_snapshot": state,
                "voice_snapshot_sha256": None,
            })
        else:
            updated.update({
                "voice_id": snapshot["profile_id"],
                "voice_profile_version": snapshot["profile_version"],
                "voice_snapshot": "ready",
                "voice_snapshot_sha256": snapshot["snapshot_sha256"],
            })
        try:
            atomic_write_json_at(run_fd, "status.json", updated)
        except ContextError as error:
            raise VoiceError(error.code, str(error)) from error
        return updated

    def _degrade_default_at(self, run_fd: int, error: VoiceError) -> dict:
        try:
            status = read_json_at(run_fd, "status.json")
        except ContextError as context_error:
            raise VoiceError(context_error.code, str(context_error)) from context_error
        self._write_status_at(run_fd, status, None, "unavailable")
        return {
            "task_id": status["task_id"],
            "voice_id": DEFAULT_VOICE_ID,
            "voice_snapshot": "unavailable",
            "degraded": True,
            "error": {"code": error.code, "message": str(error)},
        }

    @staticmethod
    def _existing_nonready_state(status: dict, selector: str | int | None) -> dict | None:
        state = status.get("voice_snapshot")
        default_requested = selector is None or (
            isinstance(selector, str) and selector.strip().casefold() in {DEFAULT_VOICE_ID, "自然默认"}
        )
        if state == "ready":
            raise VoiceError("snapshot_missing", "status.json requires an existing Voice Snapshot")
        if state == "legacy":
            if not default_requested:
                raise VoiceError("snapshot_conflict", "legacy task Voice cannot be changed")
            expected = {
                "voice_id": "legacy-natural",
                "voice_profile_version": None,
                "voice_snapshot_sha256": None,
            }
            if any(status.get(key) != value for key, value in expected.items()):
                raise VoiceError("hash_mismatch", "status.json legacy Voice state is invalid")
            return {
                "task_id": status["task_id"],
                "voice_id": "legacy-natural",
                "voice_snapshot": "legacy",
                "verified": True,
            }
        if state == "unavailable":
            if not default_requested:
                raise VoiceError("snapshot_conflict", "unavailable natural-default task Voice cannot be changed")
            expected = {
                "voice_id": DEFAULT_VOICE_ID,
                "voice_profile_version": None,
                "voice_snapshot_sha256": None,
            }
            if any(status.get(key) != value for key, value in expected.items()):
                raise VoiceError("hash_mismatch", "status.json unavailable Voice state is invalid")
            return {
                "task_id": status["task_id"],
                "voice_id": DEFAULT_VOICE_ID,
                "voice_snapshot": "unavailable",
                "verified": True,
            }
        if state not in {None, "pending"}:
            raise VoiceError("schema_unsupported", "status.json Voice Snapshot state is invalid")
        return None

    @staticmethod
    def _has_partial_voice_state(status: dict) -> bool:
        return any(field in status for field in VOICE_STATUS_FIELDS)

    def create_snapshot(
        self,
        run_dir: Path | str,
        selector: str | int | None = None,
        *,
        selection_source: str | None = None,
    ) -> dict:
        if selection_source is None:
            selection_source = "default" if selector is None else "request"
        if selection_source not in SELECTION_SOURCES:
            raise VoiceError("invalid_input", "unsupported Voice selection source")
        requested_default = selector is None or (
            isinstance(selector, str) and selector.strip().casefold() in {DEFAULT_VOICE_ID, "自然默认"}
        )
        try:
            with run_directory(run_dir) as (run_fd, _):
                with run_lock(run_fd):
                    task_id = self._task_id_at(run_fd)
                    status = read_json_at(run_fd, "status.json")
                    existing = self._read_snapshot_at(run_fd)
                    if existing is not None:
                        state = status.get("voice_snapshot")
                        if state in {"legacy", "unavailable"}:
                            raise VoiceError("snapshot_conflict", f"{state} task cannot adopt a Voice Snapshot")
                        if state not in {None, "pending", "ready"}:
                            raise VoiceError("schema_unsupported", "status.json Voice Snapshot state is invalid")
                        effective_selector = selector
                        if effective_selector is None and state == "pending":
                            pending_voice = status.get("voice_id")
                            if isinstance(pending_voice, str) and pending_voice:
                                effective_selector = pending_voice
                        same = effective_selector is None
                        same = same or (
                            isinstance(effective_selector, str)
                            and effective_selector.strip().casefold() in {
                                existing["profile_id"].casefold(),
                                existing["profile"]["label"].casefold(),
                            }
                        )
                        if not same:
                            try:
                                same = self.resolve(effective_selector)["id"] == existing["profile_id"]
                            except VoiceError:
                                same = False
                        if not same:
                            raise VoiceError("snapshot_conflict", "task already owns a different Voice Snapshot")
                        if existing["task_id"] != task_id:
                            raise VoiceError("snapshot_conflict", "Voice Snapshot task_id does not match run directory")
                        if state == "ready":
                            expected = {
                                "voice_id": existing["profile_id"],
                                "voice_profile_version": existing["profile_version"],
                                "voice_snapshot_sha256": existing["snapshot_sha256"],
                            }
                            if any(status.get(key) != value for key, value in expected.items()):
                                raise VoiceError("hash_mismatch", "status.json does not match Voice Snapshot")
                        self._write_status_at(run_fd, status, existing, "ready")
                        return existing
                    if status.get("voice_snapshot") is None:
                        if self._has_partial_voice_state(status):
                            raise VoiceError("snapshot_missing", "status.json has incomplete Voice Snapshot state")
                        status = self._write_status_at(run_fd, status, None, "legacy")
                    existing_state = self._existing_nonready_state(status, selector)
                    if existing_state is not None:
                        return existing_state
                    if selector is None and status.get("voice_snapshot") == "pending":
                        pending_voice = status.get("voice_id")
                        if isinstance(pending_voice, str) and pending_voice:
                            selector = pending_voice
                            requested_default = selector.casefold() == DEFAULT_VOICE_ID
                            if selection_source == "default":
                                selection_source = status.get("voice_selection_source", "content_contract")
                                if selection_source not in SELECTION_SOURCES:
                                    raise VoiceError("schema_unsupported", "status.json Voice selection source is invalid")
                    try:
                        profile = self.resolve(selector)
                    except VoiceError as error:
                        if requested_default and error.code in {"registry_invalid", "registry_unavailable"}:
                            return self._degrade_default_at(run_fd, error)
                        raise
                    pending_voice = status.get("voice_id") if status.get("voice_snapshot") == "pending" else None
                    if isinstance(pending_voice, str) and pending_voice and profile["id"] != pending_voice:
                        raise VoiceError("snapshot_conflict", "selected Voice does not match pending status")
                    snapshot = {
                        "schema_version": SCHEMA_VERSION,
                        "task_id": task_id,
                        "created_at": _now(),
                        "selection_source": selection_source,
                        "profile_id": profile["id"],
                        "profile_version": profile["version"],
                        "profile_sha256": canonical_sha256(profile),
                        "profile": profile,
                    }
                    snapshot["snapshot_sha256"] = canonical_sha256(snapshot)
                    validate_snapshot(snapshot)
                    try:
                        published = publish_json_once_at(run_fd, SNAPSHOT_FILE, snapshot)
                    except ContextError as error:
                        raise VoiceError(error.code, str(error)) from error
                    if not published:
                        winner = self._read_snapshot_at(run_fd)
                        if winner is None or winner["profile_id"] != profile["id"]:
                            raise VoiceError("snapshot_conflict", "Voice Snapshot publication winner conflicts")
                        snapshot = winner
                    self._write_status_at(run_fd, status, snapshot, "ready")
                    return snapshot
        except RunFsError as error:
            raise VoiceError(error.code, str(error)) from error
        except ContextError as error:
            raise VoiceError(error.code, str(error)) from error

    def verify_run(self, run_dir: Path | str) -> dict:
        try:
            with run_directory(run_dir) as (run_fd, _):
                with run_lock(run_fd):
                    result, _ = self._verify_at(run_fd)
                    return result
        except RunFsError as error:
            raise VoiceError(error.code, str(error)) from error
        except ContextError as error:
            raise VoiceError(error.code, str(error)) from error

    def read_task_profile(self, run_dir: Path | str) -> dict | None:
        try:
            with run_directory(run_dir) as (run_fd, _):
                with run_lock(run_fd):
                    verified, snapshot = self._verify_at(run_fd)
        except RunFsError as error:
            raise VoiceError(error.code, str(error)) from error
        except ContextError as error:
            raise VoiceError(error.code, str(error)) from error
        if verified["voice_snapshot"] != "ready":
            return None
        return snapshot["profile"]

    def _verify_at(self, run_fd: int) -> tuple[dict, dict | None]:
        task_id = self._task_id_at(run_fd)
        status = read_json_at(run_fd, "status.json")
        snapshot = self._read_snapshot_at(run_fd)
        if snapshot is None:
            state = status.get("voice_snapshot")
            if state is None:
                if self._has_partial_voice_state(status):
                    raise VoiceError("snapshot_missing", "status.json has incomplete Voice Snapshot state")
                self._write_status_at(run_fd, status, None, "legacy")
                return ({"task_id": task_id, "voice_id": "legacy-natural", "voice_snapshot": "legacy", "verified": True}, None)
            if (
                state == "legacy"
                and status.get("voice_id") == "legacy-natural"
                and status.get("voice_profile_version") is None
                and status.get("voice_snapshot_sha256") is None
            ):
                return ({"task_id": task_id, "voice_id": "legacy-natural", "voice_snapshot": "legacy", "verified": True}, None)
            if (
                state == "unavailable"
                and status.get("voice_id") == DEFAULT_VOICE_ID
                and status.get("voice_profile_version") is None
                and status.get("voice_snapshot_sha256") is None
            ):
                return ({"task_id": task_id, "voice_id": DEFAULT_VOICE_ID, "voice_snapshot": "unavailable", "verified": True}, None)
            raise VoiceError("snapshot_missing", "Voice Snapshot is required by task status")
        if snapshot["task_id"] != task_id:
            raise VoiceError("hash_mismatch", "Voice Snapshot task_id does not match run directory")
        expected = {
            "voice_id": snapshot["profile_id"],
            "voice_profile_version": snapshot["profile_version"],
            "voice_snapshot": "ready",
            "voice_snapshot_sha256": snapshot["snapshot_sha256"],
        }
        if any(status.get(key) != value for key, value in expected.items()):
            raise VoiceError("hash_mismatch", "status.json does not match Voice Snapshot")
        return ({
            "task_id": task_id,
            "voice_id": snapshot["profile_id"],
            "profile_version": snapshot["profile_version"],
            "voice_snapshot": "ready",
            "snapshot_sha256": snapshot["snapshot_sha256"],
            "verified": True,
        }, snapshot)


def ensure_learning_allowed(run_dir: Path | str, *, task_id: str | None = None) -> dict:
    result = VoicePresetStore().verify_run(run_dir)
    if task_id is not None and result["task_id"] != task_id:
        raise VoiceError("unknown_id", "learning source task_id does not match run directory")
    if result["voice_snapshot"] == "ready" and result["voice_id"] != DEFAULT_VOICE_ID:
        raise VoiceError("learning_isolated", "non-default Voice tasks are excluded from Style Observation learning")
    return result
