"""Linux-only descriptor anchoring and locking shared by runtime domains."""
from __future__ import annotations

from contextlib import contextmanager
import errno
import fcntl
import os
from pathlib import Path
import stat
from typing import Iterator


class RunFsError(ValueError):
    """Stable failure raised by the shared run filesystem boundary."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


@contextmanager
def run_directory(run_dir: Path | str) -> Iterator[tuple[int, Path]]:
    """Anchor an existing run directory without following path-component symlinks."""
    if not isinstance(run_dir, (str, os.PathLike)) or not os.fspath(run_dir):
        raise RunFsError("invalid_input", "run_dir must be a non-empty path")
    try:
        path = Path(run_dir).expanduser()
    except (OSError, RuntimeError, ValueError) as error:
        raise RunFsError("path_escape", "run directory is unsafe") from error
    parts = path.parts[1:] if path.is_absolute() else path.parts
    if any(part in {".", ".."} for part in parts):
        raise RunFsError("path_escape", "run directory contains an unsafe path component")
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    start = path.anchor if path.is_absolute() else "."
    try:
        descriptor = os.open(start, flags)
    except FileNotFoundError as error:
        raise RunFsError("not_initialized", "run directory is missing") from error
    except (OSError, ValueError) as error:
        raise RunFsError("path_escape", "run directory is unsafe") from error
    try:
        for part in parts:
            try:
                next_descriptor = os.open(part, flags, dir_fd=descriptor)
            except FileNotFoundError as error:
                raise RunFsError("not_initialized", "run directory is missing") from error
            except (OSError, ValueError) as error:
                try:
                    mode = os.stat(part, dir_fd=descriptor, follow_symlinks=False).st_mode
                except FileNotFoundError as missing:
                    raise RunFsError("not_initialized", "run directory is missing") from missing
                except (OSError, ValueError) as inspect_error:
                    raise RunFsError("path_escape", "run directory is unsafe") from inspect_error
                if stat.S_ISLNK(mode):
                    raise RunFsError("path_escape", "run directory contains a symlink") from error
                if getattr(error, "errno", None) in {errno.ENOTDIR, errno.ENOENT}:
                    raise RunFsError("not_initialized", "run directory is missing") from error
                raise RunFsError("path_escape", "run directory is unsafe") from error
            os.close(descriptor)
            descriptor = next_descriptor
        yield descriptor, Path(f"/proc/self/fd/{descriptor}")
    finally:
        os.close(descriptor)


def resolved_descriptor_path(descriptor: int) -> Path:
    """Resolve the object held by one anchored Linux descriptor."""
    try:
        return Path(os.readlink(f"/proc/self/fd/{descriptor}"))
    except OSError as error:
        raise RunFsError("path_escape", "cannot resolve anchored descriptor") from error


def resolved_run_directory(run_fd: int) -> Path:
    """Resolve an anchored Linux directory descriptor after possible ancestor moves."""
    return resolved_descriptor_path(run_fd)


@contextmanager
def run_lock(run_fd: int) -> Iterator[None]:
    """Serialize Handoff and Voice updates for one anchored run."""
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(".handoff.lock", flags, 0o600, dir_fd=run_fd)
    except OSError as error:
        raise RunFsError("path_escape", "run lock is unsafe") from error
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise RunFsError("path_escape", "run lock must be a regular file")
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
    finally:
        os.close(descriptor)
