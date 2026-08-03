"""Bundled Persona Skill templates."""
from __future__ import annotations

from importlib.resources import files
import os
from pathlib import Path
from pathlib import PurePosixPath


_TEMPLATES = (
    {
        "id": "khazix-writer",
        "label": "卡兹克科技观察（实验）",
        "version": "2",
        "description": "从 Article-only 实验 Profile 提炼的科技观察人格；不注入真实身份、经历或第一人称事实。",
        "best_for": ["analysis", "review", "opinion", "tutorial"],
        "source": "khazix-writer/SKILL.md",
    },
)
_BY_ID = {item["id"]: item for item in _TEMPLATES}


class TemplateSourceError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def list_templates() -> dict:
    """Return the explicit built-in Persona template catalog."""
    return {
        "templates": [
            {
                key: list(value) if key == "best_for" else value
                for key, value in item.items()
                if key != "source"
            }
            for item in _TEMPLATES
        ]
    }


def source_identity(
    source: str | os.PathLike[str], *, check_ambiguity: bool = True
) -> tuple[str, str]:
    """Classify one selector without reading an external source."""
    try:
        value = os.fspath(source)
    except (TypeError, ValueError) as error:
        raise TemplateSourceError("invalid_input", "Persona source must be a text path") from error
    if not isinstance(value, str) or not value:
        raise TemplateSourceError("invalid_input", "Persona source must be a non-empty text path")
    if isinstance(source, os.PathLike):
        return "external", value
    builtin_id = value.removeprefix("builtin:")
    template = _BY_ID.get(builtin_id)
    if value.startswith("builtin:"):
        if template is None:
            raise TemplateSourceError("unknown_id", "unknown built-in Persona template")
        return "builtin", builtin_id
    if template is None:
        return "external", value
    if not check_ambiguity:
        return "builtin", builtin_id
    try:
        Path(value).expanduser().lstat()
    except FileNotFoundError:
        return "builtin", builtin_id
    except (OSError, RuntimeError, ValueError) as error:
        raise TemplateSourceError("path_escape", "Persona source path is unsafe") from error
    raise TemplateSourceError(
        "ambiguous_source",
        "ambiguous Persona source; use builtin:" + value + " or an explicit path",
    )


def load_builtin(source: str | os.PathLike[str]) -> tuple[str, bytes] | None:
    """Return one bundled template as a stable logical path and bytes."""
    kind, value = source_identity(source)
    if kind == "builtin":
        template = _BY_ID[value]
        resource = files("writing_master").joinpath(
            "persona_templates", *PurePosixPath(template["source"]).parts
        )
        try:
            return f"builtin:{value}", resource.read_bytes()
        except FileNotFoundError as error:
            raise TemplateSourceError("not_initialized", "built-in Persona template is missing") from error
        except OSError as error:
            raise TemplateSourceError("io_error", "cannot read built-in Persona template") from error
    return None


def external_source_path(source: str | os.PathLike[str]) -> Path:
    """Preserve one explicit external Persona source path."""
    value = os.fspath(source)
    return Path(value).expanduser()
