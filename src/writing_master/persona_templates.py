"""Bundled Persona Skill templates."""
from __future__ import annotations

import os
from pathlib import Path


_ROOT = Path(__file__).with_name("persona_templates")
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


def resolve_source(source: str | os.PathLike[str]) -> Path:
    """Resolve a built-in template ID, or preserve an external source path."""
    value = os.fspath(source)
    template = _BY_ID.get(value)
    if template is not None:
        return _ROOT / template["source"]
    return Path(value).expanduser()
