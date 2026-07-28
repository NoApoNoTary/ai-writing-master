from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from writing_master.commands.research import main
from writing_master.personal_context import ContextStore, normalized_content_sha256
from writing_master.research_brief import make_evidence_id


class ResearchCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name) / "home"
        self.run = Path(self.temporary.name) / "runs" / "TASK-C-001"
        self.run.mkdir(parents=True)
        (self.run / "status.json").write_text('{"task_id":"TASK-C-001"}', encoding="utf-8")
        (self.run / "brief.md").write_text("# Synthetic brief\n", encoding="utf-8")
        ContextStore(self.home).initialize()
        ContextStore(self.home).create_snapshot(self.run, materials=[])
        self.environment = patch.dict(os.environ, {"WRITING_MASTER_HOME": str(self.home)})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def draft_path(self) -> Path:
        candidates = []
        for index in range(1, 4):
            text = f"Synthetic evidence {index}."
            evidence = {
                "source_url": f"https://example.test/{index}",
                "source_date": "2026-07-27",
                "content_sha256": normalized_content_sha256(text),
            }
            evidence.update({
                "evidence_id": make_evidence_id(evidence),
                "source_title": "Synthetic Source",
                "publisher": "Synthetic Research",
                "observed_at": "2026-07-27T11:30:00+00:00",
                "evidence_text": text,
            })
            candidates.append({
                "candidate_id": f"topic-{index:03d}", "topic": f"Topic {index}",
                "heat": {"score": 8, "basis": "Recent sources.", "as_of": "2026-07-27T12:00:00+00:00", "evidence_ids": [evidence["evidence_id"]]},
                "audience": "Developers", "angle": "Verified execution", "evidence": [evidence],
                "scores": {
                    "heat": {"value": 8, "rationale": "Recent."},
                    "user_value": {"value": 8, "rationale": "Useful."},
                    "differentiation": {"value": 7, "rationale": "Specific."},
                    "author_fit": {"value": 5, "rationale": "Limited empty profile.", "references": [{"kind": "profile", "profile_id": "author-default", "revision": 0, "content_sha256": "eb7877b5514de357ac7596eb7f894c85985b67f0e1ff39158d1f2cb121351452"}]},
                },
                "rationale": "Synthetic candidate.",
            })
        path = Path(self.temporary.name) / "draft.json"
        path.write_text(json.dumps({"schema_version": 1, "candidates": candidates}), encoding="utf-8")
        return path

    def invoke(self, argv: list[str]) -> tuple[int, str, str]:
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_save_and_verify_json(self):
        code, output, error = self.invoke(["save", str(self.run), str(self.draft_path()), "--json"])
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(json.loads(output)["task_id"], "TASK-C-001")

        code, output, error = self.invoke(["verify", str(self.run), "--json"])
        self.assertEqual((code, error), (0, ""))
        self.assertTrue(json.loads(output)["verified"])

    def test_invalid_draft_is_machine_readable(self):
        broken = Path(self.temporary.name) / "broken.json"
        broken.write_text("{", encoding="utf-8")
        code, output, error = self.invoke(["save", str(self.run), str(broken), "--json"])
        self.assertEqual((code, error), (1, ""))
        self.assertEqual(json.loads(output)["error"]["code"], "invalid_json")

        deeply_nested = Path(self.temporary.name) / "deeply-nested.json"
        deeply_nested.write_text(
            '{"schema_version":1,"candidates":' + ("[" * 2000) + "0" + ("]" * 2000) + "}",
            encoding="utf-8",
        )
        code, output, error = self.invoke([
            "save", str(self.run), str(deeply_nested), "--json",
        ])
        self.assertEqual((code, error), (1, ""))
        self.assertEqual(json.loads(output)["error"]["code"], "invalid_json")
        self.assertNotIn("Traceback", output)

    def test_surrogate_evidence_text_is_machine_readable_invalid_input(self):
        path = self.draft_path()
        draft = json.loads(path.read_text(encoding="utf-8"))
        draft["candidates"][0]["evidence"][0]["evidence_text"] = "\ud800"
        path.write_text(json.dumps(draft), encoding="utf-8")

        code, output, error = self.invoke(["save", str(self.run), str(path), "--json"])

        self.assertEqual((code, error), (1, ""))
        self.assertEqual(json.loads(output)["error"]["code"], "invalid_input")
        self.assertNotIn("Traceback", output)

    def test_missing_and_symlinked_drafts_are_machine_readable(self):
        missing = Path(self.temporary.name) / "missing.json"
        code, output, error = self.invoke(["save", str(self.run), str(missing), "--json"])
        self.assertEqual((code, error), (1, ""))
        self.assertEqual(json.loads(output)["error"]["code"], "not_initialized")

        code, output, error = self.invoke(["save", str(self.run), "bad\x00draft", "--json"])
        self.assertEqual((code, error), (1, ""))
        self.assertEqual(json.loads(output)["error"]["code"], "path_escape")

        target = self.draft_path()
        link = Path(self.temporary.name) / "draft-link.json"
        link.symlink_to(target)
        code, output, error = self.invoke(["save", str(self.run), str(link), "--json"])
        self.assertEqual((code, error), (1, ""))
        self.assertEqual(json.loads(output)["error"]["code"], "path_escape")

    def test_fifo_draft_returns_without_blocking(self):
        fifo = Path(self.temporary.name) / "draft.fifo"
        os.mkfifo(fifo)
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "writing_master.commands.research",
                "save",
                str(self.run),
                str(fifo),
                "--json",
            ],
            text=True,
            capture_output=True,
            env=environment,
            timeout=2,
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["error"]["code"], "path_escape")

    def test_different_existing_brief_returns_duplicate_json_error(self):
        path = self.draft_path()
        self.assertEqual(self.invoke(["save", str(self.run), str(path), "--json"])[0], 0)
        value = json.loads(path.read_text(encoding="utf-8"))
        value["candidates"][0]["topic"] = "Different topic"
        path.write_text(json.dumps(value), encoding="utf-8")
        code, output, error = self.invoke(["save", str(self.run), str(path), "--json"])
        self.assertEqual((code, error), (1, ""))
        self.assertEqual(json.loads(output)["error"]["code"], "duplicate")

    def test_argparse_error_is_machine_readable(self):
        code, output, error = self.invoke(["save", "--json"])
        self.assertEqual((code, error), (1, ""))
        self.assertEqual(json.loads(output)["error"]["code"], "invalid_input")

    def test_direct_module_help(self):
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
        result = subprocess.run(
            [sys.executable, "-m", "writing_master.commands.research", "--help"],
            text=True,
            capture_output=True,
            env=environment,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("save", result.stdout)
        self.assertIn("verify", result.stdout)

    def test_text_errors_go_to_stderr(self):
        code, output, error = self.invoke(["verify", str(self.run)])
        self.assertEqual((code, output), (1, ""))
        self.assertTrue(error.startswith("research:"))


if __name__ == "__main__":
    unittest.main()
