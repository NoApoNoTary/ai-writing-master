from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
import tempfile
import unittest
from pathlib import Path

from writing_master.commands.voice import main


class VoiceCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.run = Path(self.temporary.name) / "run"
        self.run.mkdir()
        (self.run / "status.json").write_text(json.dumps({
            "task_id": "TASK-CLI", "voice_snapshot": "pending",
        }), encoding="utf-8")

    def invoke(self, argv: list[str]) -> tuple[int, str, str]:
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_list_snapshot_verify_and_json_errors_are_stable(self) -> None:
        code, output, error = self.invoke(["list", "--json"])
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(json.loads(output)["default_id"], "natural-default")

        code, output, error = self.invoke(["snapshot", str(self.run), "clear-analytical", "--json"])
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(json.loads(output)["profile_id"], "clear-analytical")

        code, output, error = self.invoke(["verify-run", str(self.run), "--json"])
        self.assertEqual((code, error), (0, ""))
        self.assertTrue(json.loads(output)["verified"])

        code, output, error = self.invoke(["snapshot", str(self.run), "missing", "--json"])
        self.assertEqual((code, error), (1, ""))
        self.assertEqual(json.loads(output)["error"]["code"], "snapshot_conflict")

    def test_parser_errors_honor_json_request(self) -> None:
        code, output, error = self.invoke(["snapshot", "--json"])
        self.assertEqual((code, error), (1, ""))
        self.assertEqual(json.loads(output)["error"]["code"], "invalid_input")

    def test_unknown_voice_before_snapshot_returns_current_choices(self) -> None:
        code, output, error = self.invoke(["snapshot", str(self.run), "missing", "--json"])
        self.assertEqual((code, error), (1, ""))
        failure = json.loads(output)["error"]
        self.assertEqual(failure["code"], "unknown_voice")
        self.assertEqual(len(failure["available"]), 5)
        self.assertIn("magazine-dialogue-editor", [item["id"] for item in failure["available"]])


if __name__ == "__main__":
    unittest.main()
