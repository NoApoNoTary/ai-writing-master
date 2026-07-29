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

from writing_master.commands.learn import main
from writing_master.voice_presets import VoicePresetStore


def candidate() -> dict:
    return {
        "source": {
            "task_id": "TASK-N",
            "baseline": {"path": "draft-v1.md", "sha256": "a" * 64},
            "edited": {"path": "final.md", "sha256": "b" * 64},
        },
        "evidence": [{"kind": "snippet", "before": "before", "after": "after"}],
        "rule": {
            "dimension": "expression",
            "guidance": "Lead with the executable judgment.",
            "scope": {"kind": "global", "value": ""},
        },
        "proposal": {"model": "MODEL", "prompt": "Extract one candidate rule."},
    }


class LearnCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name) / "home"
        self.run = Path(self.temporary.name) / "run"
        self.run.mkdir()
        (self.run / "status.json").write_text(json.dumps({"task_id": "TASK-N"}), encoding="utf-8")
        self.environment = patch.dict(os.environ, {"WRITING_MASTER_HOME": str(self.home)})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def invoke(self, argv: list[str]) -> tuple[int, str, str]:
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def write_candidate(self) -> Path:
        path = self.home / "candidate.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(candidate()), encoding="utf-8")
        return path

    def test_propose_decide_show_json(self):
        candidate_path = self.write_candidate()
        code, output, error = self.invoke(["propose", str(candidate_path), "--run-dir", str(self.run), "--json"])
        self.assertEqual((code, error), (1, ""))
        self.assertEqual(json.loads(output)["error"]["code"], "not_initialized")

        from writing_master.personal_context import ContextStore

        ContextStore().initialize()
        code, output, error = self.invoke(["propose", str(candidate_path), "--run-dir", str(self.run), "--json"])
        self.assertEqual((code, error), (0, ""))
        observation = json.loads(output)
        self.assertEqual(observation["status"], "proposed")

        code, output, error = self.invoke([
            "decide", observation["observation_id"], "--accept", "--json",
        ])
        self.assertEqual((code, error), (0, ""))
        decision = json.loads(output)
        self.assertEqual(decision["observation"]["status"], "accepted")
        self.assertEqual(decision["style"]["status"], "ready")

        code, output, error = self.invoke(["show", "--json"])
        self.assertEqual((code, error), (0, ""))
        shown = json.loads(output)
        self.assertEqual(shown["style"], decision["style"])
        self.assertEqual([item["observation_id"] for item in shown["observations"]], [observation["observation_id"]])

    def test_text_propose_prints_only_observation_id(self):
        from writing_master.personal_context import ContextStore

        ContextStore().initialize()
        code, output, error = self.invoke(["propose", str(self.write_candidate()), "--run-dir", str(self.run)])
        self.assertEqual((code, error), (0, ""))
        self.assertRegex(output, r"^observation-[0-9a-f]{16}\n$")

    def test_missing_or_malformed_candidate_is_machine_readable(self):
        missing = self.home / "missing.json"
        code, output, error = self.invoke(["propose", str(missing), "--run-dir", str(self.run), "--json"])
        self.assertEqual((code, error), (1, ""))
        self.assertEqual(json.loads(output)["error"]["code"], "invalid_input")

        malformed = self.home / "bad.json"
        malformed.parent.mkdir(parents=True, exist_ok=True)
        malformed.write_text("{", encoding="utf-8")
        code, output, error = self.invoke(["propose", str(malformed), "--run-dir", str(self.run), "--json"])
        self.assertEqual((code, error), (1, ""))
        self.assertEqual(json.loads(output)["error"]["code"], "invalid_json")

        nonstandard = self.home / "nonstandard.json"
        nonstandard.write_text('{"source":NaN}', encoding="utf-8")
        code, output, error = self.invoke(["propose", str(nonstandard), "--run-dir", str(self.run), "--json"])
        self.assertEqual((code, error), (1, ""))
        self.assertEqual(json.loads(output)["error"]["code"], "invalid_json")

        invalid_utf8 = self.home / "invalid-utf8.json"
        invalid_utf8.write_bytes(b"\xff")
        code, output, error = self.invoke(["propose", str(invalid_utf8), "--run-dir", str(self.run), "--json"])
        self.assertEqual((code, error), (1, ""))
        self.assertEqual(json.loads(output)["error"]["code"], "invalid_json")

    def test_decision_flag_is_required_and_mutually_exclusive(self):
        code, output, error = self.invoke(["decide", "observation-deadbeefdeadbeef", "--json"])
        self.assertEqual((code, error), (1, ""))
        self.assertEqual(json.loads(output)["error"]["code"], "invalid_input")

        code, output, error = self.invoke([
            "decide", "observation-deadbeefdeadbeef", "--accept", "--reject", "--json",
        ])
        self.assertEqual((code, error), (1, ""))
        self.assertEqual(json.loads(output)["error"]["code"], "invalid_input")

        from writing_master.personal_context import ContextStore

        ContextStore().initialize()
        code, output, error = self.invoke([
            "decide", "observation-deadbeefdeadbeef", "--accept", "--json",
        ])
        self.assertEqual((code, error), (1, ""))
        self.assertEqual(json.loads(output)["error"]["code"], "unknown_id")

    def test_text_errors_go_to_stderr_with_learn_prefix(self):
        code, output, error = self.invoke(["show"])
        self.assertEqual((code, output), (1, ""))
        self.assertTrue(error.startswith("learn: "))

    def test_propose_run_dir_excludes_non_default_voice_and_checks_task_id(self):
        from writing_master.personal_context import ContextStore

        ContextStore().initialize()
        candidate_path = self.write_candidate()
        run = Path(self.temporary.name) / "non-default-run"
        run.mkdir()
        (run / "status.json").write_text(json.dumps({
            "task_id": "TASK-N", "voice_snapshot": "pending",
        }), encoding="utf-8")
        VoicePresetStore().create_snapshot(run, "clear-analytical")

        code, output, error = self.invoke(["propose", str(candidate_path), "--run-dir", str(run), "--json"])
        self.assertEqual((code, error), (1, ""))
        self.assertEqual(json.loads(output)["error"]["code"], "learning_isolated")

        (run / "status.json").write_text(json.dumps({"task_id": "OTHER"}), encoding="utf-8")
        code, output, error = self.invoke(["propose", str(candidate_path), "--run-dir", str(run), "--json"])
        self.assertEqual((code, error), (1, ""))
        self.assertEqual(json.loads(output)["error"]["code"], "hash_mismatch")

    def test_error_output_uses_parsed_json_option(self):
        code, output, error = self.invoke(["propose", str(self.write_candidate()), "--json"])
        self.assertEqual((code, error), (1, ""))
        self.assertEqual(json.loads(output)["error"]["code"], "invalid_input")

        code, output, error = self.invoke(["show", "--j"])
        self.assertEqual((code, error), (1, ""))
        self.assertEqual(json.loads(output)["error"]["code"], "not_initialized")

        code, output, error = self.invoke(["propose", "--run-dir", str(self.run), "--", "--json"])
        self.assertEqual((code, output), (1, ""))
        self.assertTrue(error.startswith("learn: "))

    def test_direct_module_help(self):
        environment = {**os.environ, "PYTHONPATH": str(Path.cwd() / "src")}
        result = subprocess.run(
            [sys.executable, "-m", "writing_master.commands.learn", "--help"],
            capture_output=True,
            env=environment,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("propose", result.stdout)
        self.assertIn("decide", result.stdout)
        self.assertIn("show", result.stdout)
