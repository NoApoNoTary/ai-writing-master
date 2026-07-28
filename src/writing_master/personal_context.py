"""Deterministic storage foundation for Personal Context documents."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
from typing import Iterator
import unicodedata


SCHEMA_VERSION = 1
CONTEXT_DIRECTORY = "personal-context"
PROFILE_FILE = "author-profile.json"
STYLE_FILE = "style-profile.json"
INDEX_FILE = "knowledge-index.json"
APPROVAL_FILE = "context-approvals.json"
SNAPSHOT_FILE = "personal-context-snapshot.json"
USAGE_FILE = "context-usage.json"
CONTEXT_MATERIALS_DIRECTORY = "context-materials"
PROFILE_CONTENT_FIELDS = (
    "identity",
    "expertise",
    "content_directions",
    "values",
    "expression",
    "avoid",
    "provenance",
)
MATERIAL_KINDS = (
    "experiences",
    "opinions",
    "cases",
    "references",
    "previous_articles",
)
SOURCE_KINDS = (
    "user_provided",
    "user_confirmed",
    "external_reference",
    "editorial_inference",
)
VISIBILITIES = ("private", "publishable", "ask_before_use")
MATERIAL_STATUSES = ("active", "disabled")
INGEST_KINDS = ("managed_add", "legacy_import")
ALLOWED_USES = ("background", "paraphrase", "quote")
_RFC3339 = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


class ContextError(ValueError):
    """A stable Personal Context contract failure."""

    def __init__(self, code: str, message: str | None = None):
        self.code = code
        super().__init__(message or code)


def canonical_json_bytes(value: object) -> bytes:
    """Return the contract's canonical UTF-8 JSON representation."""
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ContextError("invalid_input", "value is not canonical JSON") from error


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def empty_profile() -> dict:
    content = {
        "identity": {},
        "expertise": [],
        "content_directions": [],
        "values": [],
        "expression": {"tone": []},
        "avoid": [],
        "provenance": {"kind": "empty"},
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "empty",
        "profile_id": "author-default",
        "revision": 0,
        **content,
        "content_sha256": canonical_sha256(content),
    }


def empty_style() -> dict:
    content = {"rules": [], "provenance": {"kind": "empty"}}
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "empty",
        "profile_id": "style-default",
        "revision": 0,
        **content,
        "content_sha256": canonical_sha256(content),
    }


def empty_index() -> dict:
    return {"schema_version": SCHEMA_VERSION, "revision": 0, "items": []}


def _profile_content(document: object, *, error_code: str) -> dict:
    """Validate confirmed profile content without accepting runtime-managed fields."""
    if not isinstance(document, dict) or set(document) != set(PROFILE_CONTENT_FIELDS):
        raise ContextError(error_code, "profile content fields are unsupported")
    identity = document["identity"]
    expression = document["expression"]
    if (
        not isinstance(identity, dict)
        or any(not isinstance(key, str) or not isinstance(value, str) for key, value in identity.items())
        or not isinstance(expression, dict)
        or set(expression) != {"tone"}
        or not isinstance(expression["tone"], list)
        or any(not isinstance(value, str) for value in expression["tone"])
        or document["provenance"] != {"kind": "user_confirmed"}
    ):
        raise ContextError(error_code, "profile content is invalid")
    for field in ("expertise", "content_directions", "values", "avoid"):
        if not isinstance(document[field], list) or any(not isinstance(value, str) for value in document[field]):
            raise ContextError(error_code, "profile content is invalid")
    return {field: document[field] for field in PROFILE_CONTENT_FIELDS}


def _valid_rfc3339(value: object) -> bool:
    if not isinstance(value, str) or not _RFC3339.fullmatch(value):
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
        return parsed.tzinfo is not None
    except ValueError:
        return False


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalized_content_sha256(text: str) -> str:
    """Hash NFC text with only line-ending normalization, per the material contract."""
    if not isinstance(text, str):
        raise ContextError("invalid_input", "material text must be a string")
    normalized = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _material_tags(tags: object, *, error_code: str) -> list[str]:
    if tags is None:
        return []
    if not isinstance(tags, list):
        raise ContextError(error_code, "tags must be a list")
    normalized: set[str] = set()
    for tag in tags:
        if not isinstance(tag, str):
            raise ContextError(error_code, "tags must contain strings")
        tag = unicodedata.normalize("NFC", tag)
        if not tag:
            raise ContextError(error_code, "tags must be non-empty")
        normalized.add(tag)
    return sorted(normalized)


def _material_input(
    *,
    kind: object,
    title: object,
    summary: object,
    tags: object,
    source_kind: object,
    source_ref: object,
    visibility: object,
    ingest_kind: object,
    error_code: str,
) -> dict:
    if kind not in MATERIAL_KINDS or source_kind not in SOURCE_KINDS or visibility not in VISIBILITIES:
        raise ContextError(error_code, "unsupported material kind, source_kind or visibility")
    if ingest_kind not in INGEST_KINDS:
        raise ContextError(error_code, "unsupported ingest_kind")
    if not isinstance(title, str) or not title or not isinstance(summary, str):
        raise ContextError(error_code, "material title and summary are invalid")
    if not isinstance(source_ref, str) or not source_ref:
        raise ContextError(error_code, "material source_ref is invalid")
    if kind == "experiences" and source_kind not in {"user_provided", "user_confirmed"}:
        raise ContextError(error_code, "experiences require a user source_kind")
    return {
        "kind": kind,
        "title": title,
        "summary": summary,
        "tags": _material_tags(tags, error_code=error_code),
        "source_kind": source_kind,
        "source_ref": source_ref,
        "visibility": visibility,
        "ingest_kind": ingest_kind,
    }


def _item_id(kind: str, normalized_hash: str, source_kind: str) -> str:
    key = f"{kind}\0{normalized_hash}\0{source_kind}".encode("utf-8")
    return f"knowledge-{hashlib.sha256(key).hexdigest()[:16]}"


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{64}", value))


def _search_terms(query: object) -> list[str]:
    if not isinstance(query, str):
        raise ContextError("invalid_input", "search query must be a string")
    normalized = unicodedata.normalize("NFC", query).casefold()
    terms = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]+", normalized)
    if not terms:
        raise ContextError("invalid_input", "search query has no searchable terms")
    return terms


def _search_score(terms: list[str], *, title: str, tags: list[str], summary: str, content: str) -> int:
    fields = ((10, title), (7, " ".join(tags)), (5, summary), (2, content))
    score = 0
    for term in terms:
        for weight, value in fields:
            count = unicodedata.normalize("NFC", value).casefold().count(term)
            score += weight * min(count, 3)
    return score


def resolve_home(home: Path | str | None = None) -> Path:
    """Resolve an explicit home or the established WRITING_MASTER_HOME default."""
    if home is None:
        home = os.getenv("WRITING_MASTER_HOME") or Path.home() / ".writing-master"
    if not isinstance(home, (str, os.PathLike)) or not os.fspath(home):
        raise ContextError("invalid_input", "home must be a non-empty path")
    try:
        return Path(home).expanduser().resolve(strict=False)
    except (OSError, RuntimeError) as error:
        raise ContextError("path_escape", "home cannot be resolved") from error


def context_root(home: Path | str | None = None) -> Path:
    """Return the Personal Context root and reject a root symlink escape."""
    home_path = resolve_home(home)
    root = home_path / CONTEXT_DIRECTORY
    try:
        root.resolve(strict=False).relative_to(home_path)
    except (OSError, RuntimeError, ValueError) as error:
        raise ContextError("path_escape", "personal context root escapes home") from error
    return root


def safe_relative_path(value: str) -> str:
    """Validate the contract's canonical slash-separated relative paths."""
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ContextError("path_escape", "non-empty slash-separated relative path required")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or not path.parts
        or any(part in {".", ".."} for part in path.parts)
        or path.as_posix() != value
    ):
        raise ContextError("path_escape", f"unsafe relative path: {value}")
    return value


def safe_path(root: Path | str, relative: str, *, must_exist: bool = False) -> Path:
    """Resolve a managed path without allowing an absolute or symlink escape."""
    relative = safe_relative_path(relative)
    try:
        root_path = Path(root).resolve(strict=False)
        candidate = root_path / relative
        resolved = candidate.resolve(strict=must_exist)
        resolved.relative_to(root_path)
    except FileNotFoundError as error:
        raise ContextError("not_initialized", f"missing managed path: {relative}") from error
    except (OSError, RuntimeError, ValueError) as error:
        raise ContextError("path_escape", f"managed path escapes root: {relative}") from error
    return candidate


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant: {value}")


def read_json(path: Path | str) -> dict:
    """Read one strict JSON object without masking corruption as an empty state."""
    path = Path(path)
    with _directory_fd(path.parent) as directory_fd:
        return read_json_at(directory_fd, path.name)


@contextmanager
def _directory_fd(path: Path | str, *, create: bool = False) -> Iterator[int]:
    """Anchor managed operations to one directory, rejecting a final symlink."""
    directory = Path(path)
    if create:
        directory.mkdir(parents=True, exist_ok=True)
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(directory, flags)
    except FileNotFoundError as error:
        raise ContextError("not_initialized", f"missing managed directory: {directory}") from error
    except OSError as error:
        raise ContextError("path_escape", f"unsafe managed directory: {directory}") from error
    try:
        yield descriptor
    finally:
        os.close(descriptor)


@contextmanager
def managed_directory_fd(root_fd: int, relative: str, *, create: bool = False) -> Iterator[int]:
    """Open a managed descendant without traversing an unchecked path segment."""
    relative = safe_relative_path(relative)
    current_fd = os.dup(root_fd)
    try:
        for part in PurePosixPath(relative).parts:
            if create:
                try:
                    os.mkdir(part, 0o700, dir_fd=current_fd)
                except FileExistsError:
                    pass
            try:
                next_fd = os.open(
                    part,
                    os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
                    dir_fd=current_fd,
                )
            except FileNotFoundError as error:
                raise ContextError("not_initialized", f"missing managed directory: {relative}") from error
            except OSError as error:
                raise ContextError("path_escape", f"unsafe managed directory: {relative}") from error
            os.close(current_fd)
            current_fd = next_fd
        yield current_fd
    finally:
        os.close(current_fd)


def _managed_name(value: str) -> str:
    safe_relative_path(value)
    if "/" in value:
        raise ContextError("path_escape", f"managed file must be local to its directory: {value}")
    return value


def read_json_at(directory_fd: int, name: str) -> dict:
    """Read a strict JSON object through an already-anchored directory FD."""
    name = _managed_name(name)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(name, flags, dir_fd=directory_fd)
    except FileNotFoundError as error:
        raise ContextError("not_initialized", f"missing JSON document: {name}") from error
    except OSError as error:
        raise ContextError("path_escape", f"unsafe JSON document: {name}") from error
    try:
        with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
            text = handle.read()
        value = json.loads(text, parse_constant=_reject_json_constant)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise ContextError("invalid_json", f"invalid JSON document: {name}") from error
    if not isinstance(value, dict):
        raise ContextError("invalid_json", f"JSON object required: {name}")
    return value


def read_bytes_at(directory_fd: int, name: str) -> bytes:
    """Read one local managed file through an already-anchored directory FD."""
    name = _managed_name(name)
    try:
        descriptor = os.open(name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=directory_fd)
    except FileNotFoundError as error:
        raise ContextError("not_initialized", f"missing managed file: {name}") from error
    except OSError as error:
        raise ContextError("path_escape", f"unsafe managed file: {name}") from error
    try:
        with os.fdopen(descriptor, "rb") as handle:
            return handle.read()
    except OSError as error:
        raise ContextError("hash_mismatch", f"cannot read managed file: {name}") from error


def read_relative_bytes_at(root_fd: int, relative: str) -> bytes:
    """Read a slash-relative managed file beneath an anchored directory."""
    relative = safe_relative_path(relative)
    parts = PurePosixPath(relative).parts
    if len(parts) == 1:
        return read_bytes_at(root_fd, parts[0])
    with managed_directory_fd(root_fd, "/".join(parts[:-1])) as directory_fd:
        return read_bytes_at(directory_fd, parts[-1])


def write_relative_bytes_at(root_fd: int, relative: str, value: bytes) -> None:
    """Atomically write a slash-relative managed file beneath an anchored directory."""
    relative = safe_relative_path(relative)
    parts = PurePosixPath(relative).parts
    if len(parts) == 1:
        atomic_write_bytes_at(root_fd, parts[0], value)
        return
    with managed_directory_fd(root_fd, "/".join(parts[:-1]), create=True) as directory_fd:
        atomic_write_bytes_at(directory_fd, parts[-1], value)


def atomic_write_bytes_at(directory_fd: int, name: str, value: bytes) -> None:
    """Atomically write one local managed file without re-resolving its directory."""
    name = _managed_name(name)
    if not isinstance(value, bytes):
        raise ContextError("invalid_input", "managed file bytes required")
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
                    dir_fd=directory_fd,
                )
                temporary = candidate
                break
            except FileExistsError:
                continue
        if descriptor is None or temporary is None:
            raise ContextError("invalid_input", f"cannot allocate temporary file for {name}")
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = None
            handle.write(value)
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


def atomic_write_json_at(directory_fd: int, name: str, value: dict) -> None:
    """Atomically write one local managed JSON file without re-resolving its directory."""
    atomic_write_bytes_at(directory_fd, name, canonical_json_bytes(value))


def atomic_write_json(path: Path | str, value: dict) -> None:
    """Fsync a temporary canonical JSON document, then atomically replace it."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _directory_fd(path.parent) as directory_fd:
        atomic_write_json_at(directory_fd, path.name, value)


@contextmanager
def context_lock(root: Path | str) -> Iterator[None]:
    """Serialize context-store mutations across processes with an advisory lock."""
    with _directory_fd(root, create=True) as root_fd:
        with _context_lock_fd(root_fd):
            yield


@contextmanager
def _context_lock_fd(root_fd: int) -> Iterator[None]:
    """Lock a file through an anchored context directory descriptor."""
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(".personal-context.lock", flags, 0o600, dir_fd=root_fd)
    except OSError as error:
        raise ContextError("path_escape", "context lock is unsafe") from error
    with os.fdopen(descriptor, "a+", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


@contextmanager
def _usage_lock_fd(run_fd: int) -> Iterator[None]:
    """Serialize the write-once Context Usage record within one run directory."""
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(".context-usage.lock", flags, 0o600, dir_fd=run_fd)
    except OSError as error:
        raise ContextError("path_escape", "context usage lock is unsafe") from error
    with os.fdopen(descriptor, "a+", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _validate_empty_document(document: dict, expected: dict, name: str, hash_fields: tuple[str, ...] = ()) -> None:
    if (
        not isinstance(document, dict)
        or set(document) != set(expected)
        or type(document.get("schema_version")) is not int
        or document["schema_version"] != SCHEMA_VERSION
        or type(document.get("revision")) is not int
    ):
        raise ContextError("schema_unsupported", f"unsupported {name} schema")
    if hash_fields:
        payload = {field: document[field] for field in hash_fields}
        if document["content_sha256"] != canonical_sha256(payload):
            raise ContextError("hash_mismatch", f"{name} content hash does not match")
    if document != expected:
        raise ContextError("schema_unsupported", f"{name} is not the canonical empty document")


def validate_profile(document: dict) -> None:
    if not isinstance(document, dict):
        raise ContextError("schema_unsupported", "unsupported author profile schema")
    if document.get("status") == "empty":
        _validate_empty_document(
            document,
            empty_profile(),
            "author profile",
            PROFILE_CONTENT_FIELDS,
        )
        return
    required = {
        "schema_version", "status", "profile_id", "revision", "updated_at", *PROFILE_CONTENT_FIELDS,
        "content_sha256",
    }
    if (
        set(document) != required
        or type(document.get("schema_version")) is not int
        or document["schema_version"] != SCHEMA_VERSION
        or document.get("status") != "ready"
        or document.get("profile_id") != "author-default"
        or type(document.get("revision")) is not int
        or document["revision"] < 1
        or not _valid_rfc3339(document.get("updated_at"))
    ):
        raise ContextError("schema_unsupported", "unsupported author profile schema")
    content = _profile_content(
        {field: document[field] for field in PROFILE_CONTENT_FIELDS},
        error_code="schema_unsupported",
    )
    if document.get("content_sha256") != canonical_sha256(content):
        raise ContextError("hash_mismatch", "author profile content hash does not match")


def validate_style(document: dict) -> None:
    _validate_empty_document(document, empty_style(), "style profile", ("rules", "provenance"))


def validate_index(document: dict) -> None:
    if document == empty_index():
        _validate_empty_document(document, empty_index(), "knowledge index")
        return
    if (
        not isinstance(document, dict)
        or set(document) != {"schema_version", "revision", "items"}
        or type(document.get("schema_version")) is not int
        or document["schema_version"] != SCHEMA_VERSION
        or type(document.get("revision")) is not int
        or document["revision"] < 1
        or not isinstance(document.get("items"), list)
        or any(not isinstance(item_id, str) or not item_id for item_id in document["items"])
        or document["items"] != sorted(set(document["items"]))
    ):
        raise ContextError("schema_unsupported", "unsupported knowledge index schema")


MATERIAL_METADATA_FIELDS = {
    "schema_version",
    "item_id",
    "revision",
    "kind",
    "status",
    "title",
    "summary",
    "tags",
    "source_kind",
    "ingest_kind",
    "source_ref",
    "source_sha256",
    "normalized_content_sha256",
    "content_sha256",
    "content_path",
    "visibility",
    "created_at",
    "updated_at",
}


def validate_material_metadata(document: dict) -> None:
    if (
        not isinstance(document, dict)
        or set(document) != MATERIAL_METADATA_FIELDS
        or type(document.get("schema_version")) is not int
        or document["schema_version"] != SCHEMA_VERSION
        or not isinstance(document.get("item_id"), str)
        or not document["item_id"]
        or document["item_id"] in {".", ".."}
        or "/" in document["item_id"]
        or "\\" in document["item_id"]
        or type(document.get("revision")) is not int
        or document["revision"] < 1
        or document.get("status") not in MATERIAL_STATUSES
        or not _valid_rfc3339(document.get("created_at"))
        or not _valid_rfc3339(document.get("updated_at"))
        or not all(_is_sha256(document.get(field)) for field in (
            "source_sha256", "normalized_content_sha256", "content_sha256"
        ))
    ):
        raise ContextError("schema_unsupported", "unsupported knowledge item schema")
    values = _material_input(
        kind=document["kind"],
        title=document["title"],
        summary=document["summary"],
        tags=document["tags"],
        source_kind=document["source_kind"],
        source_ref=document["source_ref"],
        visibility=document["visibility"],
        ingest_kind=document["ingest_kind"],
        error_code="schema_unsupported",
    )
    if values["tags"] != document["tags"]:
        raise ContextError("schema_unsupported", "knowledge item tags are not canonical")
    expected_content_path = f"knowledge/{document['kind']}/{document['item_id']}/content.md"
    if document.get("content_path") != expected_content_path:
        raise ContextError("schema_unsupported", "knowledge item content path is invalid")


APPROVAL_FIELDS = {
    "approval_id",
    "item_id",
    "allowed_use",
    "status",
    "approved_at",
    "approval_sha256",
}


def _approval_sha256(approval: dict) -> str:
    return canonical_sha256({key: value for key, value in approval.items() if key != "approval_sha256"})


def validate_approval(approval: dict) -> None:
    if (
        not isinstance(approval, dict)
        or set(approval) != APPROVAL_FIELDS
        or not isinstance(approval.get("approval_id"), str)
        or not approval["approval_id"]
        or not isinstance(approval.get("item_id"), str)
        or not approval["item_id"]
        or approval.get("allowed_use") not in ALLOWED_USES
        or approval.get("status") != "approved"
        or not _valid_rfc3339(approval.get("approved_at"))
    ):
        raise ContextError("schema_unsupported", "unsupported context approval schema")
    if approval.get("approval_sha256") != _approval_sha256(approval):
        raise ContextError("hash_mismatch", "context approval hash does not match")


def validate_approval_log(document: dict, *, task_id: str | None = None) -> None:
    if (
        not isinstance(document, dict)
        or set(document) != {"schema_version", "task_id", "revision", "approvals"}
        or type(document.get("schema_version")) is not int
        or document["schema_version"] != SCHEMA_VERSION
        or not isinstance(document.get("task_id"), str)
        or not document["task_id"]
        or type(document.get("revision")) is not int
        or document["revision"] < 0
        or not isinstance(document.get("approvals"), list)
        or document["revision"] != len(document["approvals"])
        or (task_id is not None and document["task_id"] != task_id)
    ):
        raise ContextError("schema_unsupported", "unsupported context approval log")
    seen: set[tuple[str, str]] = set()
    for approval in document["approvals"]:
        validate_approval(approval)
        key = (approval["item_id"], approval["allowed_use"])
        if key in seen:
            raise ContextError("schema_unsupported", "duplicate context approval")
        seen.add(key)


TASK_SAFE_METADATA_FIELDS = {
    "schema_version",
    "item_id",
    "revision",
    "kind",
    "status",
    "title",
    "summary",
    "tags",
    "source_kind",
    "ingest_kind",
    "visibility",
}


def task_safe_metadata(metadata: dict) -> dict:
    return {field: metadata[field] for field in sorted(TASK_SAFE_METADATA_FIELDS)}


def _frozen_profile(document: dict) -> dict:
    return {
        "status": document["status"],
        "profile_id": document["profile_id"],
        "revision": document["revision"],
        "content": {field: document[field] for field in PROFILE_CONTENT_FIELDS},
        "content_sha256": document["content_sha256"],
    }


def _frozen_style(document: dict) -> dict:
    return {
        "status": document["status"],
        "profile_id": document["profile_id"],
        "revision": document["revision"],
        "content": {"rules": document["rules"], "provenance": document["provenance"]},
        "content_sha256": document["content_sha256"],
    }


def _validate_frozen_profile(document: dict) -> None:
    if (
        not isinstance(document, dict)
        or set(document) != {"status", "profile_id", "revision", "content", "content_sha256"}
        or document.get("profile_id") != "author-default"
        or type(document.get("revision")) is not int
        or not isinstance(document.get("content"), dict)
    ):
        raise ContextError("schema_unsupported", "unsupported frozen profile")
    content = document["content"]
    if document["status"] == "empty":
        expected = empty_profile()
        if document["revision"] != 0 or content != {field: expected[field] for field in PROFILE_CONTENT_FIELDS}:
            raise ContextError("schema_unsupported", "unsupported frozen empty profile")
    elif document["status"] == "ready" and document["revision"] >= 1:
        _profile_content(content, error_code="schema_unsupported")
    else:
        raise ContextError("schema_unsupported", "unsupported frozen profile status")
    if document.get("content_sha256") != canonical_sha256(content):
        raise ContextError("hash_mismatch", "frozen profile content hash does not match")


def _validate_frozen_style(document: dict) -> None:
    if (
        not isinstance(document, dict)
        or set(document) != {"status", "profile_id", "revision", "content", "content_sha256"}
        or document.get("status") != "empty"
        or document.get("profile_id") != "style-default"
        or document.get("revision") != 0
        or document.get("content") != {"rules": [], "provenance": {"kind": "empty"}}
    ):
        raise ContextError("schema_unsupported", "unsupported frozen style")
    if document.get("content_sha256") != canonical_sha256(document["content"]):
        raise ContextError("hash_mismatch", "frozen style content hash does not match")


def _validate_snapshot_material(material: dict) -> None:
    required = {
        "item_id", "kind", "metadata", "metadata_sha256", "content_sha256", "purpose", "approval", "copy_path"
    }
    if (
        not isinstance(material, dict)
        or set(material) != required
        or not isinstance(material.get("item_id"), str)
        or not material["item_id"]
        or material["item_id"] in {".", ".."}
        or "/" in material["item_id"]
        or "\\" in material["item_id"]
        or material.get("kind") not in MATERIAL_KINDS
        or material.get("purpose") not in ALLOWED_USES
        or material.get("copy_path") != f"{CONTEXT_MATERIALS_DIRECTORY}/{material.get('item_id')}.md"
        or not isinstance(material.get("metadata"), dict)
        or set(material["metadata"]) != TASK_SAFE_METADATA_FIELDS
        or not _is_sha256(material.get("metadata_sha256"))
        or not _is_sha256(material.get("content_sha256"))
    ):
        raise ContextError("schema_unsupported", "unsupported Snapshot material")
    metadata = material["metadata"]
    if (
        metadata["item_id"] != material["item_id"]
        or metadata["kind"] != material["kind"]
        or metadata["status"] != "active"
        or type(metadata["schema_version"]) is not int
        or metadata["schema_version"] != SCHEMA_VERSION
        or type(metadata["revision"]) is not int
        or metadata["revision"] < 1
    ):
        raise ContextError("schema_unsupported", "Snapshot metadata is invalid")
    normalized = _material_input(
        kind=metadata["kind"],
        title=metadata["title"],
        summary=metadata["summary"],
        tags=metadata["tags"],
        source_kind=metadata["source_kind"],
        source_ref="snapshot",
        visibility=metadata["visibility"],
        ingest_kind=metadata["ingest_kind"],
        error_code="schema_unsupported",
    )
    if normalized["tags"] != metadata["tags"]:
        raise ContextError("schema_unsupported", "Snapshot metadata tags are not canonical")
    if material["metadata_sha256"] != canonical_sha256(metadata):
        raise ContextError("hash_mismatch", "Snapshot metadata hash does not match")
    approval = material["approval"]
    if approval == {"status": "not_required"}:
        if metadata["visibility"] != "publishable":
            raise ContextError("privacy_unapproved", "Snapshot approval is missing")
    else:
        validate_approval(approval)
        if (
            metadata["visibility"] != "ask_before_use"
            or approval["item_id"] != material["item_id"]
            or approval["allowed_use"] != material["purpose"]
        ):
            raise ContextError("privacy_unapproved", "Snapshot approval does not admit material")


def validate_snapshot(document: dict) -> None:
    required = {"schema_version", "task_id", "created_at", "profile", "style", "materials", "snapshot_sha256"}
    if (
        not isinstance(document, dict)
        or set(document) != required
        or type(document.get("schema_version")) is not int
        or document["schema_version"] != SCHEMA_VERSION
        or not isinstance(document.get("task_id"), str)
        or not document["task_id"]
        or not _valid_rfc3339(document.get("created_at"))
        or not isinstance(document.get("materials"), list)
    ):
        raise ContextError("schema_unsupported", "unsupported personal context Snapshot")
    _validate_frozen_profile(document["profile"])
    _validate_frozen_style(document["style"])
    pairs = []
    for material in document["materials"]:
        _validate_snapshot_material(material)
        pairs.append((material["item_id"], material["purpose"]))
    if pairs != sorted(pairs) or len(pairs) != len(set(pairs)):
        raise ContextError("schema_unsupported", "Snapshot materials are not deterministically ordered")
    if document.get("snapshot_sha256") != canonical_sha256(
        {key: value for key, value in document.items() if key != "snapshot_sha256"}
    ):
        raise ContextError("hash_mismatch", "Snapshot hash does not match")


def validate_context_usage(document: dict, snapshot: dict) -> None:
    required = {"schema_version", "task_id", "snapshot_sha256", "status", "uses", "artifacts", "recorded_at"}
    if (
        not isinstance(document, dict)
        or set(document) != required
        or type(document.get("schema_version")) is not int
        or document["schema_version"] != SCHEMA_VERSION
        or document.get("task_id") != snapshot["task_id"]
        or document.get("snapshot_sha256") != snapshot["snapshot_sha256"]
        or document.get("status") != "complete"
        or not isinstance(document.get("uses"), list)
        or not isinstance(document.get("artifacts"), dict)
        or set(document["artifacts"]) != {"final", "acceptance"}
        or not _valid_rfc3339(document.get("recorded_at"))
    ):
        raise ContextError("schema_unsupported", "unsupported context usage")
    snapshot_pairs = {(material["item_id"], material["purpose"]) for material in snapshot["materials"]}
    for use in document["uses"]:
        if (
            not isinstance(use, dict)
            or set(use) - {"item_id", "purpose", "section", "claim_id"}
            or not {"item_id", "purpose", "section"}.issubset(use)
            or not isinstance(use["item_id"], str)
            or not isinstance(use["purpose"], str)
            or not isinstance(use["section"], str)
            or not use["section"]
            or ("claim_id" in use and (not isinstance(use["claim_id"], str) or not use["claim_id"]))
            or (use["item_id"], use["purpose"]) not in snapshot_pairs
        ):
            raise ContextError("privacy_unapproved", "context usage exceeds the Snapshot")
    for artifact in document["artifacts"].values():
        if (
            not isinstance(artifact, dict)
            or set(artifact) != {"path", "sha256"}
            or not isinstance(artifact["path"], str)
            or not _is_sha256(artifact["sha256"])
        ):
            raise ContextError("schema_unsupported", "context usage artifact is invalid")
        safe_relative_path(artifact["path"])


class ContextStore:
    """Own the three canonical empty documents under one WRITING_MASTER_HOME."""

    def __init__(self, home: Path | str | None = None):
        self.home = resolve_home(home)
        self.root = context_root(self.home)
        self._home_identity: tuple[int, int] | None = None

    def _assert_home_unchanged(self) -> None:
        if resolve_home(self.home) != self.home:
            raise ContextError("path_escape", "home path changed after ContextStore creation")

    @contextmanager
    def _root_fd(self, *, create: bool) -> Iterator[int]:
        self._assert_home_unchanged()
        try:
            if create:
                self.home.mkdir(parents=True, exist_ok=True)
            with _directory_fd(self.home) as home_fd:
                status = os.fstat(home_fd)
                identity = (status.st_dev, status.st_ino)
                if self._home_identity is None:
                    self._home_identity = identity
                elif identity != self._home_identity:
                    raise ContextError("path_escape", "home directory identity changed")
                with managed_directory_fd(home_fd, CONTEXT_DIRECTORY, create=create) as root_fd:
                    yield root_fd
        except ContextError:
            raise
        except OSError as error:
            raise ContextError("path_escape", "cannot access personal context root") from error

    @property
    def profile_path(self) -> Path:
        self._assert_home_unchanged()
        context_root(self.home)
        return safe_path(self.root, PROFILE_FILE)

    @property
    def style_path(self) -> Path:
        self._assert_home_unchanged()
        context_root(self.home)
        return safe_path(self.root, STYLE_FILE)

    @property
    def index_path(self) -> Path:
        self._assert_home_unchanged()
        context_root(self.home)
        return safe_path(self.root, INDEX_FILE)

    def _ensure_root(self) -> None:
        with self._root_fd(create=True):
            pass

    def _require_root(self) -> None:
        with self._root_fd(create=False):
            pass

    @contextmanager
    def _locked_root(self) -> Iterator[int]:
        with self._root_fd(create=True) as root_fd:
            with _context_lock_fd(root_fd):
                yield root_fd

    @contextmanager
    def locked(self) -> Iterator[None]:
        with self._locked_root():
            yield

    def initialize(self) -> dict:
        """Create missing canonical empty documents without rewriting valid ones."""
        documents = (
            (PROFILE_FILE, empty_profile, validate_profile),
            (STYLE_FILE, empty_style, validate_style),
            (INDEX_FILE, empty_index, validate_index),
        )
        with self._locked_root() as root_fd:
            values: list[dict] = []
            missing: list[tuple[str, dict]] = []
            for name, factory, validator in documents:
                try:
                    value = read_json_at(root_fd, name)
                    validator(value)
                except ContextError as error:
                    if error.code != "not_initialized":
                        raise
                    value = factory()
                    missing.append((name, value))
                values.append(value)
            for name, value in missing:
                atomic_write_json_at(root_fd, name, value)
        return {"profile": values[0], "style": values[1], "index": values[2]}

    def _read(self, name: str, validator) -> dict:
        with self._root_fd(create=False) as root_fd:
            value = read_json_at(root_fd, name)
            validator(value)
            return value

    def read_profile(self) -> dict:
        return self._read(PROFILE_FILE, validate_profile)

    def read_style(self) -> dict:
        return self._read(STYLE_FILE, validate_style)

    def read_index(self) -> dict:
        return self._read(INDEX_FILE, validate_index)

    def _read_item_metadata_at(self, root_fd: int, item_id: str) -> dict:
        _managed_name(item_id)
        for kind in MATERIAL_KINDS:
            try:
                with managed_directory_fd(root_fd, f"knowledge/{kind}/{item_id}") as item_fd:
                    metadata = read_json_at(item_fd, "metadata.json")
            except ContextError as error:
                if error.code == "not_initialized":
                    continue
                raise
            validate_material_metadata(metadata)
            if metadata["kind"] != kind:
                raise ContextError("schema_unsupported", "knowledge item directory kind does not match metadata")
            return metadata
        raise ContextError("unknown_id", f"unknown knowledge item: {item_id}")

    def add_material(
        self,
        source_path: Path | str,
        *,
        kind: str,
        title: str,
        source_kind: str,
        source_ref: str,
        visibility: str,
        tags: list[str] | None = None,
        summary: str = "",
        ingest_kind: str = "managed_add",
    ) -> dict:
        """Copy one strict UTF-8 material into the managed store with identity-local dedupe."""
        values = _material_input(
            kind=kind,
            title=title,
            summary=summary,
            tags=tags,
            source_kind=source_kind,
            source_ref=source_ref,
            visibility=visibility,
            ingest_kind=ingest_kind,
            error_code="invalid_input",
        )
        if not isinstance(source_path, (str, os.PathLike)) or not os.fspath(source_path):
            raise ContextError("invalid_input", "material source path is invalid")
        try:
            raw = Path(source_path).read_bytes()
        except OSError as error:
            raise ContextError("invalid_input", f"cannot read material source: {source_path}") from error
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ContextError("invalid_input", "material source must be strict UTF-8") from error
        if not raw:
            raise ContextError("invalid_input", "material source must not be empty")
        source_sha256 = hashlib.sha256(raw).hexdigest()
        normalized_sha256 = normalized_content_sha256(text)
        item_id = _item_id(values["kind"], normalized_sha256, values["source_kind"])
        self._require_root()
        with self._locked_root() as root_fd:
            index = read_json_at(root_fd, INDEX_FILE)
            validate_index(index)
            for existing_id in index["items"]:
                metadata = self._read_item_metadata_at(root_fd, existing_id)
                if (
                    metadata["kind"],
                    metadata["normalized_content_sha256"],
                    metadata["source_kind"],
                ) == (values["kind"], normalized_sha256, values["source_kind"]):
                    return metadata
            if item_id in index["items"]:
                raise ContextError("duplicate", "knowledge item id collision")
            created_at = _now()
            metadata = {
                "schema_version": SCHEMA_VERSION,
                "item_id": item_id,
                "revision": 1,
                "kind": values["kind"],
                "status": "active",
                "title": values["title"],
                "summary": values["summary"],
                "tags": values["tags"],
                "source_kind": values["source_kind"],
                "ingest_kind": values["ingest_kind"],
                "source_ref": values["source_ref"],
                "source_sha256": source_sha256,
                "normalized_content_sha256": normalized_sha256,
                "content_sha256": source_sha256,
                "content_path": f"knowledge/{values['kind']}/{item_id}/content.md",
                "visibility": values["visibility"],
                "created_at": created_at,
                "updated_at": created_at,
            }
            with managed_directory_fd(root_fd, f"knowledge/{values['kind']}/{item_id}", create=True) as item_fd:
                atomic_write_bytes_at(item_fd, "content.md", raw)
                atomic_write_json_at(item_fd, "metadata.json", metadata)
            updated_index = {
                "schema_version": SCHEMA_VERSION,
                "revision": index["revision"] + 1,
                "items": sorted([*index["items"], item_id]),
            }
            atomic_write_json_at(root_fd, INDEX_FILE, updated_index)
        return metadata

    def list_materials(self, *, kind: str | None = None, status: str | None = None) -> list[dict]:
        """Return deterministic metadata-only material listings."""
        if kind is not None and kind not in MATERIAL_KINDS:
            raise ContextError("invalid_input", "unsupported material kind")
        if status is not None and status not in MATERIAL_STATUSES:
            raise ContextError("invalid_input", "unsupported material status")
        self._require_root()
        with self._locked_root() as root_fd:
            index = read_json_at(root_fd, INDEX_FILE)
            validate_index(index)
            items = [self._read_item_metadata_at(root_fd, item_id) for item_id in index["items"]]
        return [
            item for item in items
            if (kind is None or item["kind"] == kind)
            and (status is None or item["status"] == status)
        ]

    def _update_material_field(
        self,
        item_id: str,
        *,
        field: str,
        value: str,
        expected_revision: int | None = None,
    ) -> dict:
        self._require_root()
        with self._locked_root() as root_fd:
            metadata = self._read_item_metadata_at(root_fd, item_id)
            if expected_revision is not None and expected_revision != metadata["revision"]:
                raise ContextError("revision_conflict", "knowledge item revision has changed")
            if metadata[field] == value:
                return metadata
            with managed_directory_fd(root_fd, f"knowledge/{metadata['kind']}/{item_id}") as item_fd:
                current = read_json_at(item_fd, "metadata.json")
                validate_material_metadata(current)
                if expected_revision is not None and expected_revision != current["revision"]:
                    raise ContextError("revision_conflict", "knowledge item revision has changed")
                if current[field] == value:
                    return current
                updated = {**current, field: value, "revision": current["revision"] + 1, "updated_at": _now()}
                validate_material_metadata(updated)
                atomic_write_json_at(item_fd, "metadata.json", updated)
                return updated

    def set_material_status(self, item_id: str, status: str) -> dict:
        if status not in MATERIAL_STATUSES:
            raise ContextError("invalid_input", "unsupported material status")
        return self._update_material_field(item_id, field="status", value=status)

    def set_material_visibility(self, item_id: str, visibility: str, *, expected_revision: int) -> dict:
        if type(expected_revision) is not int or expected_revision < 1:
            raise ContextError("invalid_input", "expected_revision must be a positive integer")
        if visibility not in VISIBILITIES:
            raise ContextError("invalid_input", "unsupported material visibility")
        return self._update_material_field(
            item_id,
            field="visibility",
            value=visibility,
            expected_revision=expected_revision,
        )

    def search_materials(
        self,
        query: str,
        *,
        kind: str | None = None,
        tag: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """Score active material metadata and bodies using deterministic literal query matches."""
        terms = _search_terms(query)
        if kind is not None and kind not in MATERIAL_KINDS:
            raise ContextError("invalid_input", "unsupported material kind")
        if tag is not None:
            tag = _material_tags([tag], error_code="invalid_input")[0]
        if type(limit) is not int or limit < 1:
            raise ContextError("invalid_input", "limit must be a positive integer")
        self._require_root()
        with self._locked_root() as root_fd:
            index = read_json_at(root_fd, INDEX_FILE)
            validate_index(index)
            scored: list[dict] = []
            for item_id in index["items"]:
                metadata = self._read_item_metadata_at(root_fd, item_id)
                if (
                    metadata["status"] != "active"
                    or (kind is not None and metadata["kind"] != kind)
                    or (tag is not None and tag not in metadata["tags"])
                ):
                    continue
                with managed_directory_fd(root_fd, f"knowledge/{metadata['kind']}/{item_id}") as item_fd:
                    raw = read_bytes_at(item_fd, "content.md")
                if hashlib.sha256(raw).hexdigest() != metadata["content_sha256"]:
                    raise ContextError("hash_mismatch", f"knowledge item content hash does not match: {item_id}")
                try:
                    content = raw.decode("utf-8")
                except UnicodeDecodeError as error:
                    raise ContextError("hash_mismatch", f"knowledge item is not UTF-8: {item_id}") from error
                score = _search_score(
                    terms,
                    title=metadata["title"],
                    tags=metadata["tags"],
                    summary=metadata["summary"],
                    content=content,
                )
                if score:
                    scored.append({**metadata, "score": score})
        return sorted(scored, key=lambda item: (-item["score"], item["item_id"]))[:limit]

    def approve(self, run_dir: Path | str, item_id: str, *, allowed_use: str) -> dict:
        """Append one task-local approval for an active, non-private material."""
        if allowed_use not in ALLOWED_USES:
            raise ContextError("invalid_input", "unsupported approval allowed_use")
        if not isinstance(run_dir, (str, os.PathLike)) or not os.fspath(run_dir):
            raise ContextError("invalid_input", "run directory is invalid")
        self._require_root()
        with self._locked_root() as root_fd:
            metadata = self._read_item_metadata_at(root_fd, item_id)
            if metadata["status"] != "active":
                raise ContextError("disabled", f"knowledge item is disabled: {item_id}")
            if metadata["visibility"] == "private":
                raise ContextError("privacy_unapproved", f"private knowledge item cannot be approved: {item_id}")
            with _directory_fd(Path(run_dir)) as run_fd:
                status = read_json_at(run_fd, "status.json")
                task_id = status.get("task_id")
                if not isinstance(task_id, str) or not task_id:
                    raise ContextError("unknown_id", "run directory has no task_id")
                try:
                    log = read_json_at(run_fd, APPROVAL_FILE)
                    validate_approval_log(log, task_id=task_id)
                except ContextError as error:
                    if error.code != "not_initialized":
                        raise
                    log = {
                        "schema_version": SCHEMA_VERSION,
                        "task_id": task_id,
                        "revision": 0,
                        "approvals": [],
                    }
                for approval in log["approvals"]:
                    if approval["item_id"] == item_id and approval["allowed_use"] == allowed_use:
                        return approval
                approval = {
                    "approval_id": "approval-" + hashlib.sha256(
                        f"{task_id}\0{item_id}\0{allowed_use}".encode("utf-8")
                    ).hexdigest()[:16],
                    "item_id": item_id,
                    "allowed_use": allowed_use,
                    "status": "approved",
                    "approved_at": _now(),
                }
                approval["approval_sha256"] = _approval_sha256(approval)
                updated = {
                    "schema_version": SCHEMA_VERSION,
                    "task_id": task_id,
                    "revision": log["revision"] + 1,
                    "approvals": [*log["approvals"], approval],
                }
                validate_approval_log(updated, task_id=task_id)
                atomic_write_json_at(run_fd, APPROVAL_FILE, updated)
                return approval

    def _admit_material_at(
        self,
        root_fd: int,
        run_fd: int,
        task_id: str,
        item_id: str,
        purpose: str,
    ) -> tuple[dict, dict]:
        metadata = self._read_item_metadata_at(root_fd, item_id)
        if metadata["status"] != "active":
            raise ContextError("disabled", f"knowledge item is disabled: {item_id}")
        if metadata["visibility"] == "private":
            raise ContextError("privacy_unapproved", f"private knowledge item cannot enter a task: {item_id}")
        if metadata["visibility"] == "publishable":
            return metadata, {"status": "not_required"}
        try:
            log = read_json_at(run_fd, APPROVAL_FILE)
            validate_approval_log(log, task_id=task_id)
        except ContextError as error:
            if error.code == "not_initialized":
                raise ContextError("privacy_unapproved", "task has no matching approval") from error
            raise
        for approval in log["approvals"]:
            if approval["item_id"] == item_id and approval["allowed_use"] == purpose:
                return metadata, approval
        raise ContextError("privacy_unapproved", "task has no matching approval")

    def admit_material(self, run_dir: Path | str, item_id: str, *, purpose: str) -> tuple[dict, dict]:
        """Resolve deterministic Snapshot admission without creating a Snapshot yet."""
        if purpose not in ALLOWED_USES:
            raise ContextError("invalid_input", "unsupported material purpose")
        if not isinstance(run_dir, (str, os.PathLike)) or not os.fspath(run_dir):
            raise ContextError("invalid_input", "run directory is invalid")
        self._require_root()
        with self._locked_root() as root_fd:
            with _directory_fd(Path(run_dir)) as run_fd:
                status = read_json_at(run_fd, "status.json")
                task_id = status.get("task_id")
                if not isinstance(task_id, str) or not task_id:
                    raise ContextError("unknown_id", "run directory has no task_id")
                return self._admit_material_at(root_fd, run_fd, task_id, item_id, purpose)

    def import_legacy(self, source_dir: Path | str, *, kind: str | None = None) -> dict:
        """Explicitly import legacy text files; one bad file never rolls back prior imports."""
        if kind is not None and kind not in MATERIAL_KINDS:
            raise ContextError("invalid_input", "unsupported legacy material kind")
        if not isinstance(source_dir, (str, os.PathLike)) or not os.fspath(source_dir):
            raise ContextError("invalid_input", "legacy source directory is invalid")
        try:
            source = Path(source_dir).resolve(strict=True)
        except OSError as error:
            raise ContextError("invalid_input", f"cannot read legacy source directory: {source_dir}") from error
        if not source.is_dir():
            raise ContextError("invalid_input", "legacy source must be a directory")
        self._require_root()
        try:
            source.relative_to(self.root.resolve(strict=True))
        except ValueError:
            pass
        else:
            raise ContextError("invalid_input", "legacy source cannot be the managed context directory")
        result = {"imported": [], "skipped": [], "failed": []}
        files = sorted(
            (path for path in source.rglob("*") if not path.is_symlink() and path.is_file()),
            key=lambda path: path.relative_to(source).as_posix(),
        )
        for path in files:
            relative = path.relative_to(source).as_posix()
            inferred_kind = kind
            if inferred_kind is None:
                parts = PurePosixPath(relative).parts
                inferred_kind = parts[0] if len(parts) > 1 and parts[0] in MATERIAL_KINDS else None
            if inferred_kind is None:
                result["failed"].append({"path": relative, "error": {"code": "invalid_input"}})
                continue
            try:
                before = set(self.read_index()["items"])
                metadata = self.add_material(
                    path,
                    kind=inferred_kind,
                    title=path.stem,
                    source_kind="user_provided",
                    source_ref=f"legacy:{relative}",
                    visibility="private",
                    ingest_kind="legacy_import",
                )
            except ContextError as error:
                result["failed"].append({"path": relative, "error": {"code": error.code}})
                continue
            target = "skipped" if metadata["item_id"] in before else "imported"
            result[target].append(metadata["item_id"])
        return result

    def _task_id_at(self, run_fd: int) -> str:
        status = read_json_at(run_fd, "status.json")
        task_id = status.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            raise ContextError("unknown_id", "run directory has no task_id")
        return task_id

    def _verify_snapshot_at(self, run_fd: int, snapshot: dict) -> None:
        validate_snapshot(snapshot)
        for material in snapshot["materials"]:
            raw = read_relative_bytes_at(run_fd, material["copy_path"])
            if hashlib.sha256(raw).hexdigest() != material["content_sha256"]:
                raise ContextError("hash_mismatch", f"Snapshot material copy hash does not match: {material['item_id']}")

    def create_snapshot(
        self,
        run_dir: Path | str,
        *,
        materials: list[tuple[str, str]] | None = None,
    ) -> dict:
        """Create one immutable task Snapshot and task-local material copies."""
        if not isinstance(run_dir, (str, os.PathLike)) or not os.fspath(run_dir):
            raise ContextError("invalid_input", "run directory is invalid")
        if materials is None:
            materials = []
        if not isinstance(materials, list):
            raise ContextError("invalid_input", "Snapshot materials must be a list")
        pairs: list[tuple[str, str]] = []
        for selection in materials:
            if (
                not isinstance(selection, (tuple, list))
                or len(selection) != 2
                or not isinstance(selection[0], str)
                or not selection[0]
                or selection[1] not in ALLOWED_USES
            ):
                raise ContextError("invalid_input", "Snapshot material must be an (item_id, purpose) pair")
            pairs.append(selection)
        pairs.sort()
        if len(pairs) != len(set(pairs)):
            raise ContextError("duplicate", "duplicate Snapshot material pair")
        self._require_root()
        with self._locked_root() as root_fd:
            with _directory_fd(Path(run_dir)) as run_fd:
                task_id = self._task_id_at(run_fd)
                try:
                    existing = read_json_at(run_fd, SNAPSHOT_FILE)
                except ContextError as error:
                    if error.code != "not_initialized":
                        raise
                else:
                    validate_snapshot(existing)
                    if existing["task_id"] != task_id:
                        raise ContextError("snapshot_conflict", "Snapshot task_id does not match run directory")
                    existing_pairs = [(item["item_id"], item["purpose"]) for item in existing["materials"]]
                    if existing_pairs != pairs:
                        raise ContextError("snapshot_conflict", "task already owns a different Snapshot")
                    self._verify_snapshot_at(run_fd, existing)
                    return existing

                profile = read_json_at(root_fd, PROFILE_FILE)
                style = read_json_at(root_fd, STYLE_FILE)
                validate_profile(profile)
                validate_style(style)
                snapshot_materials: list[dict] = []
                copies: dict[str, bytes] = {}
                for item_id, purpose in pairs:
                    metadata, approval = self._admit_material_at(root_fd, run_fd, task_id, item_id, purpose)
                    with managed_directory_fd(root_fd, f"knowledge/{metadata['kind']}/{item_id}") as item_fd:
                        raw = read_bytes_at(item_fd, "content.md")
                    if hashlib.sha256(raw).hexdigest() != metadata["content_sha256"]:
                        raise ContextError("hash_mismatch", f"knowledge item content hash does not match: {item_id}")
                    copy_path = f"{CONTEXT_MATERIALS_DIRECTORY}/{item_id}.md"
                    copies[copy_path] = raw
                    projection = task_safe_metadata(metadata)
                    snapshot_materials.append({
                        "item_id": item_id,
                        "kind": metadata["kind"],
                        "metadata": projection,
                        "metadata_sha256": canonical_sha256(projection),
                        "content_sha256": metadata["content_sha256"],
                        "purpose": purpose,
                        "approval": dict(approval),
                        "copy_path": copy_path,
                    })
                snapshot = {
                    "schema_version": SCHEMA_VERSION,
                    "task_id": task_id,
                    "created_at": _now(),
                    "profile": _frozen_profile(profile),
                    "style": _frozen_style(style),
                    "materials": snapshot_materials,
                }
                snapshot["snapshot_sha256"] = canonical_sha256(snapshot)
                validate_snapshot(snapshot)
                for copy_path, raw in copies.items():
                    try:
                        existing_copy = read_relative_bytes_at(run_fd, copy_path)
                    except ContextError as error:
                        if error.code != "not_initialized":
                            raise
                        write_relative_bytes_at(run_fd, copy_path, raw)
                    else:
                        if existing_copy != raw:
                            raise ContextError("snapshot_conflict", "existing material copy conflicts with Snapshot")
                atomic_write_json_at(run_fd, SNAPSHOT_FILE, snapshot)
                return snapshot

    def record_usage(
        self,
        run_dir: Path | str,
        *,
        uses: list[dict],
        artifact_paths: dict[str, str],
    ) -> dict:
        """Write one immutable Context Usage record with runtime-computed artifact hashes."""
        if not isinstance(run_dir, (str, os.PathLike)) or not os.fspath(run_dir):
            raise ContextError("invalid_input", "run directory is invalid")
        if not isinstance(uses, list) or not isinstance(artifact_paths, dict) or set(artifact_paths) != {"final", "acceptance"}:
            raise ContextError("invalid_input", "uses and final/acceptance artifact paths are required")
        with _directory_fd(Path(run_dir)) as run_fd:
            with _usage_lock_fd(run_fd):
                task_id = self._task_id_at(run_fd)
                snapshot = read_json_at(run_fd, SNAPSHOT_FILE)
                validate_snapshot(snapshot)
                if snapshot["task_id"] != task_id:
                    raise ContextError("hash_mismatch", "Snapshot task_id does not match run directory")
                artifacts: dict[str, dict] = {}
                for name, path in artifact_paths.items():
                    if not isinstance(path, str):
                        raise ContextError("invalid_input", "artifact path must be a string")
                    raw = read_relative_bytes_at(run_fd, path)
                    artifacts[name] = {"path": path, "sha256": hashlib.sha256(raw).hexdigest()}
                usage = {
                    "schema_version": SCHEMA_VERSION,
                    "task_id": task_id,
                    "snapshot_sha256": snapshot["snapshot_sha256"],
                    "status": "complete",
                    "uses": uses,
                    "artifacts": artifacts,
                    "recorded_at": _now(),
                }
                validate_context_usage(usage, snapshot)
                try:
                    existing = read_json_at(run_fd, USAGE_FILE)
                except ContextError as error:
                    if error.code != "not_initialized":
                        raise
                else:
                    validate_context_usage(existing, snapshot)
                    if existing["uses"] == usage["uses"] and existing["artifacts"] == usage["artifacts"]:
                        return existing
                    raise ContextError("duplicate", "task already owns a different Context Usage record")
                atomic_write_json_at(run_fd, USAGE_FILE, usage)
                return usage

    def verify_run(self, run_dir: Path | str) -> dict:
        """Verify Snapshot, frozen approvals, local copies, usage and final artifacts."""
        if not isinstance(run_dir, (str, os.PathLike)) or not os.fspath(run_dir):
            raise ContextError("invalid_input", "run directory is invalid")
        with _directory_fd(Path(run_dir)) as run_fd:
            task_id = self._task_id_at(run_fd)
            snapshot = read_json_at(run_fd, SNAPSHOT_FILE)
            validate_snapshot(snapshot)
            if snapshot["task_id"] != task_id:
                raise ContextError("hash_mismatch", "Snapshot task_id does not match run directory")
            self._verify_snapshot_at(run_fd, snapshot)
            usage = read_json_at(run_fd, USAGE_FILE)
            validate_context_usage(usage, snapshot)
            for name, artifact in usage["artifacts"].items():
                raw = read_relative_bytes_at(run_fd, artifact["path"])
                if hashlib.sha256(raw).hexdigest() != artifact["sha256"]:
                    raise ContextError("hash_mismatch", f"context usage {name} artifact hash does not match")
            return {
                "task_id": task_id,
                "snapshot_sha256": snapshot["snapshot_sha256"],
                "context_usage_sha256": canonical_sha256(usage),
                "verified": True,
            }

    def update_profile(self, content: dict, *, expected_revision: int) -> dict:
        """Atomically replace confirmed Profile content with optimistic revision control."""
        if type(expected_revision) is not int or expected_revision < 0:
            raise ContextError("invalid_input", "expected_revision must be a non-negative integer")
        self._require_root()
        with self._locked_root() as root_fd:
            current = read_json_at(root_fd, PROFILE_FILE)
            validate_profile(current)
            if expected_revision != current["revision"]:
                raise ContextError("revision_conflict", "profile revision has changed")
            content = _profile_content(content, error_code="invalid_input")
            content_sha256 = canonical_sha256(content)
            if current["status"] == "ready" and current["content_sha256"] == content_sha256:
                return current
            updated = {
                "schema_version": SCHEMA_VERSION,
                "status": "ready",
                "profile_id": "author-default",
                "revision": current["revision"] + 1,
                "updated_at": _now(),
                **content,
                "content_sha256": content_sha256,
            }
            atomic_write_json_at(root_fd, PROFILE_FILE, updated)
        return updated


def initialize(home: Path | str | None = None) -> dict:
    """Convenience entry point for the one-time Context Store initialization."""
    return ContextStore(home).initialize()
