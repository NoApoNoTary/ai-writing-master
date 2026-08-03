"""Task-local, human-readable writing contract artifact."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Mapping

from writing_master.personal_context import atomic_write_bytes

SPEC_FILE = "spec.md"
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

class SpecError(ValueError):
    pass

def _lines(value: object) -> list[str]:
    if value is None:
        return ["（未提供）"]
    if isinstance(value, str):
        return [value] if value else ["（未提供）"]
    if isinstance(value, (list, tuple)) and all(isinstance(item, str) for item in value):
        return list(value) or ["（无）"]
    raise SpecError("spec field must be a string or list of strings")

def render_spec(contract: Mapping[str, object], *, version: int = 1) -> str:
    if not isinstance(contract, Mapping):
        raise SpecError("contract must be a mapping")
    if type(version) is not int or version < 1:
        raise SpecError("version must be a positive integer")
    title = contract.get("title", "Writing Spec")
    if not isinstance(title, str) or not title.strip():
        raise SpecError("title must be a non-empty string")
    lines = [f"# {title.strip()}", "", f"- spec_version: {version}", "- state: frozen", ""]
    for heading, field in SPEC_FIELDS:
        lines.extend([f"## {heading}", ""])
        lines.extend(f"- {item}" for item in _lines(contract.get(field)))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"

def save_spec(run_dir: Path | str, contract: Mapping[str, object], *, version: int = 1) -> dict:
    run = Path(run_dir).expanduser()
    if not run.is_dir():
        raise SpecError("run directory is missing")
    text = render_spec(contract, version=version)
    target = run / SPEC_FILE
    atomic_write_bytes(target, text.encode("utf-8"))
    return {"path": SPEC_FILE, "version": version, "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "state": "frozen"}

def spec_sha256(run_dir: Path | str) -> str:
    path = Path(run_dir).expanduser() / SPEC_FILE
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError as error:
        raise SpecError("spec.md is missing") from error
