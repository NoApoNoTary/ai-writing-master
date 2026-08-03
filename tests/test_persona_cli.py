from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from writing_master.cli import main as root_main
from writing_master.commands.persona import main


class PersonaCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.run = self.root / "run"
        self.run.mkdir()
        (self.run / "status.json").write_text(json.dumps({"task_id": "TASK-PERSONA-CLI"}), encoding="utf-8")
        self.skill = self.root / "SKILL.md"
        self.skill.write_text("---\nname: persona\nversion: 3\n---\nPersona\n", encoding="utf-8")
        self.brief = self.root / "brief.md"
        self.brief.write_text("Adopted: framing\nBoundary: evidence\n", encoding="utf-8")

    def invoke(self, argv: list[str]) -> tuple[int, str, str]:
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_snapshot_and_verify_json(self) -> None:
        code, output, error = self.invoke([
            "snapshot",
            str(self.run),
            str(self.skill),
            str(self.brief),
            "--mode", "reference",
            "--content-type", "review",
            "--background", "none",
            "--json",
        ])
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(json.loads(output)["source_version"], "3")

        code, output, error = self.invoke(["verify-run", str(self.run), "--json"])
        self.assertEqual((code, error), (0, ""))
        self.assertTrue(json.loads(output)["verified"])

    def test_list_exposes_builtin_templates(self) -> None:
        code, output, error = self.invoke(["list", "--json"])

        self.assertEqual((code, error), (0, ""))
        templates = json.loads(output)["templates"]
        self.assertEqual(templates[0]["id"], "khazix-writer")
        self.assertEqual(templates[0]["label"], "卡兹克科技观察（实验）")

    def test_snapshot_accepts_builtin_template_id(self) -> None:
        code, output, error = self.invoke([
            "snapshot",
            str(self.run),
            "khazix-writer",
            str(self.brief),
            "--mode", "reference",
            "--content-type", "analysis",
            "--background", "none",
            "--json",
        ])

        self.assertEqual((code, error), (0, ""))
        result = json.loads(output)
        self.assertEqual(result["source_input"], "khazix-writer")
        self.assertIn("卡兹克科技观察", (self.run / "persona-skill.md").read_text(encoding="utf-8"))

    def test_parser_errors_and_root_registration(self) -> None:
        code, output, error = self.invoke(["snapshot", "--json"])
        self.assertEqual((code, error), (1, ""))
        self.assertEqual(json.loads(output)["error"]["code"], "invalid_input")

        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(root_main(["--help"]), 0)
        self.assertIn("persona", output.getvalue())

    def test_write_failure_is_machine_readable(self) -> None:
        with mock.patch("writing_master.persona.atomic_write_json_at", side_effect=OSError("blocked")):
            code, output, error = self.invoke([
                "snapshot",
                str(self.run),
                str(self.skill),
                str(self.brief),
                "--mode", "author",
                "--content-type", "analysis",
                "--background", "default",
                "--json",
            ])
        self.assertEqual((code, error), (1, ""))
        self.assertEqual(json.loads(output)["error"]["code"], "io_error")

    def test_invalid_task_file_is_machine_readable(self) -> None:
        (self.run / "persona-skill.md").mkdir()
        code, output, error = self.invoke([
            "snapshot",
            str(self.run),
            str(self.skill),
            str(self.brief),
            "--mode", "author",
            "--content-type", "analysis",
            "--background", "default",
            "--json",
        ])
        self.assertEqual((code, error), (1, ""))
        self.assertEqual(json.loads(output)["error"]["code"], "path_escape")


if __name__ == "__main__":
    unittest.main()
