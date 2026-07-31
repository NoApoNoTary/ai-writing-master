import tempfile
import unittest
from pathlib import Path

from writing_master.image_pipeline import CoverPipeline


class ImagePipelineTests(unittest.TestCase):
    def test_failed_generation_blocks_without_touching_canonical_or_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            canonical = root / "cover.png"
            canonical.write_bytes(b"old-canonical")
            calls = []

            def generate(attempt):
                calls.append(attempt)
                raise RuntimeError("API error (500)")

            result = CoverPipeline(
                provider="openai",
                model="gpt-image-2",
                request_type="text-to-image",
                prompt_path="prompts/cover.md",
            ).run(generate, lambda _: True, canonical)

            self.assertEqual(result["status"], "blocked_waiting_user")
            self.assertEqual(calls, [1, 2])
            self.assertEqual(canonical.read_bytes(), b"old-canonical")
            self.assertFalse((root / "cover-fallback.html").exists())

    def test_visual_qa_failure_does_not_upload_or_update(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "raw.png"
            raw.write_bytes(b"raw image")
            canonical = root / "cover.png"
            uploaded = []
            updated = []

            def generate(_attempt):
                return raw

            result = CoverPipeline(
                provider="openai",
                model="gpt-image-2",
                request_type="reference-edit",
                prompt_path="prompts/cover.md",
                reference_paths=["refs/source.png"],
            ).run(
                generate,
                lambda _: {"passed": False},
                canonical,
                upload=uploaded.append,
                update_draft=updated.append,
            )

            self.assertEqual(result["status"], "blocked_waiting_user")
            self.assertFalse(canonical.exists())
            self.assertEqual(uploaded, [])
            self.assertEqual(updated, [])
            self.assertEqual(result["provenance"]["request_type"], "reference-edit")
            self.assertEqual(len(result["provenance"]["output_sha256"]), 64)

    def test_visual_qa_pass_promotes_and_calls_callbacks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "raw.png"
            raw.write_bytes(b"raw image")
            canonical = root / "cover.png"
            uploaded = []
            updated = []

            result = CoverPipeline(
                provider="openai",
                model="gpt-image-2",
                request_type="text-to-image",
                prompt_path="prompts/cover.md",
            ).run(
                lambda _attempt: raw,
                lambda _: {"passed": True},
                canonical,
                upload=uploaded.append,
                update_draft=updated.append,
            )

            self.assertEqual(result["status"], "accepted")
            self.assertEqual(canonical.read_bytes(), raw.read_bytes())
            self.assertEqual(uploaded, [canonical])
            self.assertEqual(updated, [canonical])
            self.assertEqual(len(result["provenance"]["output_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
