"""Small fail-fast cover gate: raw generation is never canonical by itself."""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
import shutil
from typing import Any, Callable, Literal, Mapping


ImageState = Literal[
    "planned",
    "prompt_ready",
    "generating",
    "generated_raw",
    "visual_qa_passed",
    "accepted",
    "retrying",
    "blocked_waiting_user",
]

_FAILURE_CATEGORIES = {
    "auth",
    "timeout",
    "4xx",
    "5xx",
    "response_format",
    "output_missing",
    "reference_not_applied",
    "visual_qa_failed",
    "generation_error",
}


class ImagePipelineError(ValueError):
    pass


def sha256_file(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify_generation_failure(error: object) -> str:
    text = str(error).lower()
    if "timeout" in text or "timed out" in text:
        return "timeout"
    for code in ("401", "403"):
        if code in text or "auth" in text or "credential" in text:
            return "auth"
    if any(code in text for code in ("400", "404", "422")):
        return "4xx"
    if any(code in text for code in ("500", "502", "503", "504")):
        return "5xx"
    if "reference" in text and ("not applied" in text or "ignored" in text):
        return "reference_not_applied"
    if "response" in text and ("format" in text or "json" in text):
        return "response_format"
    if "missing" in text or "not found" in text:
        return "output_missing"
    return "generation_error"


@dataclass
class CoverPipeline:
    provider: str
    model: str
    request_type: Literal["text-to-image", "reference-edit"]
    prompt_path: str
    reference_paths: list[str] = field(default_factory=list)
    max_retries: int = 1
    state: ImageState = "planned"
    attempts: int = 0
    raw_path: str | None = None
    response_status: int | None = None
    failure_category: str | None = None
    failure_message: str | None = None
    output_sha256: str | None = None

    def transition(self, target: ImageState) -> None:
        allowed: dict[ImageState, set[ImageState]] = {
            "planned": {"prompt_ready"},
            "prompt_ready": {"generating"},
            "generating": {"generated_raw", "retrying", "blocked_waiting_user"},
            "generated_raw": {"visual_qa_passed", "retrying", "blocked_waiting_user"},
            "visual_qa_passed": {"accepted"},
            "retrying": {"generating", "blocked_waiting_user"},
            "accepted": set(),
            "blocked_waiting_user": set(),
        }
        if target not in allowed[self.state]:
            raise ImagePipelineError(f"invalid image transition {self.state} -> {target}")
        self.state = target

    def _record_failure(self, error: object, category: str | None = None) -> None:
        selected = category or classify_generation_failure(error)
        if selected not in _FAILURE_CATEGORIES:
            selected = "generation_error"
        self.failure_category = selected
        self.failure_message = str(error)
        if self.attempts <= self.max_retries:
            self.transition("retrying")
        else:
            self.transition("blocked_waiting_user")

    def provenance(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "request_type": self.request_type,
            "prompt_path": self.prompt_path,
            "reference_paths": list(self.reference_paths),
            "status": self.state,
            "response_status": self.response_status,
            "attempts": self.attempts,
            "output_sha256": self.output_sha256,
        }

    def failure_report(self) -> dict[str, Any]:
        return {
            "status": self.state,
            "provider": self.provider,
            "model": self.model,
            "request_type": self.request_type,
            "attempts": self.attempts,
            "failure_category": self.failure_category or "generation_error",
            "failure_message": self.failure_message or "",
            "raw_path": self.raw_path,
            "prompt_path": self.prompt_path,
            "reference_paths": list(self.reference_paths),
            "next_action": "retry, switch image backend, reduce text requirements, or defer visual delivery",
            "provenance": self.provenance(),
        }

    def accept(self, canonical_path: str | Path) -> str:
        if self.state != "visual_qa_passed" or not self.raw_path:
            raise ImagePipelineError("only visual_qa_passed output can become canonical")
        source = Path(self.raw_path)
        if not source.is_file():
            raise ImagePipelineError("raw output is missing")
        destination = Path(canonical_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        self.output_sha256 = sha256_file(source)
        self.transition("accepted")
        return str(destination)

    def run(
        self,
        generate: Callable[[int], str | Path],
        visual_qa: Callable[[Path], bool | Mapping[str, Any]],
        canonical_path: str | Path,
        *,
        upload: Callable[[Path], Any] | None = None,
        update_draft: Callable[[Path], Any] | None = None,
    ) -> dict[str, Any]:
        """Generate, QA, and promote; upload/update callbacks run only after acceptance."""
        self.transition("prompt_ready")
        while True:
            self.transition("generating")
            self.attempts += 1
            try:
                raw = Path(generate(self.attempts))
                if not raw.is_file():
                    raise ImagePipelineError("output missing")
                self.raw_path = str(raw)
                self.output_sha256 = sha256_file(raw)
                self.transition("generated_raw")
                qa_result = visual_qa(raw)
                passed = bool(qa_result if isinstance(qa_result, bool) else qa_result.get("passed"))
                if not passed:
                    self._record_failure("visual QA failed", "visual_qa_failed")
                    if self.state == "retrying":
                        continue
                    return self.failure_report()
                self.transition("visual_qa_passed")
                accepted_path = Path(self.accept(canonical_path))
                if upload:
                    upload(accepted_path)
                if update_draft:
                    update_draft(accepted_path)
                return {"status": self.state, "canonical_path": str(accepted_path), "provenance": self.provenance()}
            except Exception as error:
                if self.state == "accepted":
                    raise
                status = getattr(error, "status", None)
                if isinstance(status, int):
                    self.response_status = status
                if self.state == "generated_raw":
                    self.transition("retrying" if self.attempts <= self.max_retries else "blocked_waiting_user")
                    self.failure_category = classify_generation_failure(error)
                    self.failure_message = str(error)
                else:
                    self.failure_category = classify_generation_failure(error)
                    self.failure_message = str(error)
                    if self.state == "generating":
                        self.transition("retrying" if self.attempts <= self.max_retries else "blocked_waiting_user")
                    elif self.state == "visual_qa_passed":
                        self.transition("blocked_waiting_user")
                if self.state == "retrying":
                    continue
                return self.failure_report()
