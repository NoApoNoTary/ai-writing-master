from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from writing_master.cli import main
from writing_master.personal_context import ContextStore


def profile(name: str) -> dict:
    return {
        "identity": {"display_name": name},
        "expertise": ["Python"],
        "content_directions": ["software"],
        "values": ["evidence first"],
        "expression": {"tone": ["concise"]},
        "avoid": ["filler"],
        "provenance": {"kind": "user_confirmed"},
    }


class ContextCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name) / "home"
        self.environment = patch.dict(os.environ, {"WRITING_MASTER_HOME": str(self.home)})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def invoke(self, argv: list[str]) -> tuple[int, str, str]:
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(["context", *argv])
        return code, stdout.getvalue(), stderr.getvalue()

    def write_profile(self, name: str) -> Path:
        path = self.home / f"{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(profile(name)), encoding="utf-8")
        return path

    def write_material(self) -> Path:
        path = Path(self.temporary.name) / "orbit-17.md"
        path.write_text("Orbit 17 synthetic material", encoding="utf-8")
        return path

    def write_run(self) -> Path:
        run = Path(self.temporary.name) / "runs" / "TASK-001"
        run.mkdir(parents=True)
        (run / "status.json").write_text(json.dumps({"task_id": "TASK-001"}), encoding="utf-8")
        return run

    def test_init_and_empty_profile_show_json(self):
        code, output, error = self.invoke(["init", "--json"])

        self.assertEqual(code, 0)
        self.assertEqual(error, "")
        self.assertEqual(json.loads(output)["profile"]["revision"], 0)

        code, output, error = self.invoke(["profile", "show", "--json"])

        self.assertEqual(code, 0)
        self.assertEqual(error, "")
        self.assertEqual(json.loads(output)["revision"], 0)

    def test_uninitialized_profile_show_returns_machine_readable_error(self):
        code, output, error = self.invoke(["profile", "show", "--json"])

        self.assertEqual(code, 1)
        self.assertEqual(error, "")
        self.assertEqual(json.loads(output)["error"]["code"], "not_initialized")

    def test_two_profile_set_operations_increment_revision(self):
        self.invoke(["init"])
        first = self.write_profile("ROLE_A")
        second = self.write_profile("ROLE_B")

        code, output, error = self.invoke(
            ["profile", "set", str(first), "--expected-revision", "0", "--json"]
        )
        self.assertEqual(code, 0)
        self.assertEqual(error, "")
        self.assertEqual(json.loads(output)["revision"], 1)

        code, output, error = self.invoke(
            ["profile", "set", str(second), "--expected-revision", "1", "--json"]
        )
        self.assertEqual(code, 0)
        self.assertEqual(error, "")
        self.assertEqual(json.loads(output)["revision"], 2)

    def test_stale_profile_set_returns_json_conflict_and_preserves_latest_revision(self):
        self.invoke(["init"])
        current = self.write_profile("ROLE_A")
        stale = self.write_profile("ROLE_B")
        self.invoke(["profile", "set", str(current), "--expected-revision", "0"])

        code, output, error = self.invoke(
            ["profile", "set", str(stale), "--expected-revision", "0", "--json"]
        )

        self.assertEqual(code, 1)
        self.assertEqual(error, "")
        self.assertEqual(json.loads(output)["error"]["code"], "revision_conflict")
        code, output, _ = self.invoke(["profile", "show", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["revision"], 1)

    def test_identical_profile_is_a_noop_but_stale_revision_still_conflicts(self):
        self.invoke(["init"])
        current = self.write_profile("ROLE_A")
        _, first_output, _ = self.invoke(
            ["profile", "set", str(current), "--expected-revision", "0", "--json"]
        )

        code, output, error = self.invoke(
            ["profile", "set", str(current), "--expected-revision", "1", "--json"]
        )
        self.assertEqual(code, 0)
        self.assertEqual(error, "")
        self.assertEqual(json.loads(output), json.loads(first_output))

        code, output, error = self.invoke(
            ["profile", "set", str(current), "--expected-revision", "0", "--json"]
        )
        self.assertEqual(code, 1)
        self.assertEqual(error, "")
        self.assertEqual(json.loads(output)["error"]["code"], "revision_conflict")

    def test_json_input_errors_are_machine_readable(self):
        self.invoke(["init"])
        missing = self.home / "missing.json"

        code, output, error = self.invoke(
            ["profile", "set", str(missing), "--expected-revision", "0", "--json"]
        )
        self.assertEqual(code, 1)
        self.assertEqual(error, "")
        self.assertEqual(json.loads(output)["error"]["code"], "invalid_input")

        code, output, error = self.invoke(
            ["profile", "set", str(missing), "--expected-revision", "not-an-int", "--json"]
        )
        self.assertEqual(code, 1)
        self.assertEqual(error, "")
        self.assertEqual(json.loads(output)["error"]["code"], "invalid_input")

    def test_material_add_uses_registered_cli_contract(self):
        self.invoke(["init"])
        source = self.write_material()

        code, output, error = self.invoke([
            "material", "add", str(source), "--kind", "experiences", "--title", "Orbit 17",
            "--source-kind", "user_provided", "--source-ref", "synthetic://orbit-17",
            "--visibility", "ask_before_use", "--tag", "synthetic", "--json",
        ])

        self.assertEqual(code, 0)
        self.assertEqual(error, "")
        item = json.loads(output)
        self.assertEqual(item["kind"], "experiences")
        self.assertEqual(item["source_kind"], "user_provided")
        self.assertEqual(item["tags"], ["synthetic"])

    def test_material_lifecycle_list_and_search_commands(self):
        self.invoke(["init"])
        source = self.write_material()
        _, output, _ = self.invoke([
            "material", "add", str(source), "--kind", "experiences", "--title", "Orbit 17",
            "--source-kind", "user_provided", "--source-ref", "synthetic://orbit-17",
            "--visibility", "ask_before_use", "--tag", "synthetic", "--json",
        ])
        item = json.loads(output)

        code, output, error = self.invoke(["material", "list", "--kind", "experiences", "--json"])
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(json.loads(output)[0]["item_id"], item["item_id"])

        code, output, error = self.invoke(["material", "disable", item["item_id"], "--json"])
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(json.loads(output)["status"], "disabled")
        self.assertEqual(json.loads(self.invoke(["search", "Orbit", "--json"])[1]), [])

        _, output, _ = self.invoke(["material", "enable", item["item_id"], "--json"])
        enabled = json.loads(output)
        _, output, _ = self.invoke([
            "material", "set-visibility", item["item_id"], "publishable",
            "--expected-revision", str(enabled["revision"]), "--json",
        ])
        self.assertEqual(json.loads(output)["visibility"], "publishable")
        self.assertEqual(json.loads(self.invoke(["search", "Orbit", "--json"])[1])[0]["item_id"], item["item_id"])

    def test_explicit_legacy_import_and_task_approval_commands(self):
        self.invoke(["init"])
        legacy = Path(self.temporary.name) / "legacy" / "experiences"
        legacy.mkdir(parents=True)
        (legacy / "legacy.md").write_text("legacy synthetic", encoding="utf-8")

        code, output, error = self.invoke(["import-legacy", str(legacy.parent), "--json"])
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(len(json.loads(output)["imported"]), 1)

        source = self.write_material()
        _, output, _ = self.invoke([
            "material", "add", str(source), "--kind", "experiences", "--title", "Orbit 17",
            "--source-kind", "user_provided", "--source-ref", "synthetic://orbit-17",
            "--visibility", "ask_before_use", "--json",
        ])
        item = json.loads(output)
        code, output, error = self.invoke([
            "approve", str(self.write_run()), item["item_id"], "--allow", "background", "--json",
        ])
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(json.loads(output)["allowed_use"], "background")

    def test_snapshot_and_verify_run_commands(self):
        self.invoke(["init"])
        source = self.write_material()
        _, output, _ = self.invoke([
            "material", "add", str(source), "--kind", "experiences", "--title", "Orbit 17",
            "--source-kind", "user_provided", "--source-ref", "synthetic://orbit-17",
            "--visibility", "publishable", "--json",
        ])
        item = json.loads(output)
        run = self.write_run()
        code, output, error = self.invoke([
            "snapshot", str(run), "--material", f"{item['item_id']}:background", "--json",
        ])
        self.assertEqual((code, error), (0, ""))
        snapshot = json.loads(output)
        self.assertEqual(snapshot["materials"][0]["item_id"], item["item_id"])
        (run / "final.md").write_text("uses Orbit 17", encoding="utf-8")
        (run / "acceptance-report.md").write_text("accepted", encoding="utf-8")
        ContextStore(self.home).record_usage(
            run,
            uses=[{"item_id": item["item_id"], "purpose": "background", "section": "opening"}],
            artifact_paths={"final": "final.md", "acceptance": "acceptance-report.md"},
        )
        code, output, error = self.invoke(["verify-run", str(run), "--json"])
        self.assertEqual((code, error), (0, ""))
        self.assertTrue(json.loads(output)["verified"])

    def test_help_works(self):
        output = StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as captured:
            main(["context", "--help"])

        self.assertEqual(captured.exception.code, 0)
        self.assertIn("profile", output.getvalue())


if __name__ == "__main__":
    unittest.main()
