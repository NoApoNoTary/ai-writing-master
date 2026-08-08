import tempfile
import unittest
from pathlib import Path

from writing_master.image_pipeline import CoverPipeline, redact_secrets


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


    def test_failure_message_redacts_credentials_from_provider_error(self):
        with tempfile.TemporaryDirectory() as directory:
            canonical = Path(directory) / "cover.png"

            def generate(_attempt):
                raise RuntimeError(
                    "401 Unauthorized POST "
                    "https://api.example.com/v1/images?api_key=sk-live-AbCdEf1234567890 "
                    "headers={'Authorization': 'Bearer eyJhbGciOiJIUzI1NiJ9.payload.sig'}"
                )

            result = CoverPipeline(
                provider="example",
                model="img-1",
                request_type="text-to-image",
                prompt_path="prompts/cover.md",
                max_retries=0,
            ).run(generate, lambda _: True, canonical)

            message = result["failure_message"]
            self.assertEqual(result["failure_category"], "auth")
            self.assertEqual(result["status"], "blocked_waiting_user")
            self.assertNotIn("sk-live-AbCdEf1234567890", message)
            self.assertNotIn("eyJhbGciOiJIUzI1NiJ9.payload.sig", message)
            self.assertIn("[redacted]", message)
            self.assertIn("401", message)

    def test_redact_secrets_masks_known_shapes_and_keeps_benign_text(self):
        self.assertNotIn("AbCdEf1234567890", redact_secrets("key sk-AbCdEf1234567890 leaked"))
        self.assertNotIn("hunter2hunter2", redact_secrets('{"password": "hunter2hunter2"}'))
        self.assertNotIn("s3cr3tvalue", redact_secrets("client_secret=s3cr3tvalue"))
        self.assertNotIn("p4ssw0rd", redact_secrets("https://user:p4ssw0rd@host/path"))
        self.assertEqual(redact_secrets("API error (500)"), "API error (500)")
        self.assertEqual(redact_secrets("output missing"), "output missing")

    def test_failure_message_is_length_capped(self):
        with tempfile.TemporaryDirectory() as directory:
            canonical = Path(directory) / "cover.png"

            def generate(_attempt):
                raise RuntimeError("500 " + "x" * 2000)

            result = CoverPipeline(
                provider="example",
                model="img-1",
                request_type="text-to-image",
                prompt_path="prompts/cover.md",
                max_retries=0,
            ).run(generate, lambda _: True, canonical)

            self.assertLess(len(result["failure_message"]), 600)
            self.assertTrue(result["failure_message"].endswith("…(truncated)"))


if __name__ == "__main__":
    unittest.main()
