import json
import hashlib
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from writing_master.cli import main as cli_main
from writing_master.failure_cases import (
    SNAPSHOT_FILE,
    FailureCaseError,
    list_cases,
    propose_case,
    select_cases,
    update_case_status,
    write_snapshot,
)
from writing_master.run_spec import SpecError, save_spec, spec_sha256, verify_spec


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/failure-cases.jsonl"


class FailureCaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.library = self.root / "failure-cases.jsonl"
        self.library.write_bytes(FIXTURE.read_bytes())
        self.run = self.root / "run"
        self.run.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def test_only_active_tagged_cases_enter_snapshot(self):
        proposed = dict(list_cases(self.library)[0], id="FC-20260803-002", status="proposed")
        propose_case(proposed, self.library)
        self.assertEqual([case["id"] for case in select_cases(["headings"], path=self.library)], ["FC-20260803-001"])
        result = write_snapshot(self.run, tags=["headings"], path=self.library)
        snapshot = (self.run / SNAPSHOT_FILE).read_text(encoding="utf-8")
        self.assertEqual(result["case_ids"], ["FC-20260803-001"])
        self.assertIn("广告或内部判断只留在内部执行约束", snapshot)
        self.assertIn("逐个检查标题是否服务读者问题", snapshot)
        for excluded in (
            "FC-20260803-001", "headings", "reader-visible", "source_run",
            "source_session", "symptom", "root_cause", "notes", "synthetic",
        ):
            self.assertNotIn(excluded, snapshot)

    def test_limit_zero_selects_nothing(self):
        self.assertEqual(select_cases(["headings"], limit=0, path=self.library), [])

    def test_snapshot_is_write_once_and_conflict_safe(self):
        first = write_snapshot(self.run, tags=["headings"], path=self.library)
        before = (self.run / SNAPSHOT_FILE).read_bytes()
        self.assertEqual(write_snapshot(self.run, tags=["headings"], path=self.library), first)
        self.assertEqual((self.run / SNAPSHOT_FILE).read_bytes(), before)

        update_case_status("FC-20260803-001", "superseded", self.library)
        with self.assertRaises(FailureCaseError) as captured:
            write_snapshot(self.run, tags=["headings"], path=self.library)
        self.assertEqual(captured.exception.code, "conflict")
        self.assertEqual((self.run / SNAPSHOT_FILE).read_bytes(), before)

    def test_unknown_extension_fields_survive_status_rewrite(self):
        before = list_cases(self.library)[0]
        self.assertEqual(before["notes"], {"fixture": True, "owner": "synthetic"})
        updated = update_case_status("FC-20260803-001", "superseded", self.library)
        self.assertEqual(updated["notes"], before["notes"])
        self.assertEqual(list_cases(self.library)[0]["notes"], before["notes"])

    def test_status_update_is_persisted_and_empty_snapshot_is_valid(self):
        update_case_status("FC-20260803-001", "superseded", self.library)
        self.assertEqual(list_cases(self.library)[0]["status"], "superseded")
        result = write_snapshot(self.run, tags=["headings"], path=self.library)
        self.assertEqual(result["count"], 0)
        self.assertIn("没有匹配", (self.run / SNAPSHOT_FILE).read_text(encoding="utf-8"))

    def test_invalid_or_duplicate_case_is_rejected_without_overwriting_library(self):
        before = self.library.read_bytes()
        with self.assertRaises(FailureCaseError):
            propose_case({"id": "FC-20260803-001"}, self.library)
        self.assertEqual(self.library.read_bytes(), before)

    def test_cli_registers_and_writes_machine_readable_snapshot(self):
        case = dict(list_cases(self.library)[0], id="FC-20260803-003", status="proposed")
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(cli_main(["failure-cases", "propose", json.dumps(case), "--path", str(self.library), "--json"]), 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "proposed")
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(cli_main(["failure-cases", "snapshot", str(self.run), "--path", str(self.library), "--tag", "headings", "--json"]), 0)
        self.assertEqual(json.loads(output.getvalue())["count"], 1)

    def test_cli_json_array_and_snapshot_path_errors_are_machine_readable(self):
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(cli_main(["failure-cases", "propose", "[]", "--path", str(self.library), "--json"]), 1)
        self.assertEqual(json.loads(output.getvalue())["error"]["code"], "invalid_input")

        alias = self.root / "run-alias"
        alias.symlink_to(self.run, target_is_directory=True)
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(cli_main(["failure-cases", "snapshot", str(alias), "--path", str(self.library), "--json"]), 1)
        self.assertEqual(json.loads(output.getvalue())["error"]["code"], "path_escape")

    def test_snapshot_rejects_final_symlink(self):
        outside = self.root / "outside.md"
        outside.write_text("outside", encoding="utf-8")
        (self.run / SNAPSHOT_FILE).symlink_to(outside)
        with self.assertRaises(FailureCaseError) as captured:
            write_snapshot(self.run, tags=["headings"], path=self.library)
        self.assertEqual(captured.exception.code, "path_escape")
        self.assertEqual(outside.read_text(encoding="utf-8"), "outside")

    def test_snapshot_keeps_anchored_run_when_ancestor_is_retargeted(self):
        ancestor = self.root / "ancestor"
        original_run = ancestor / "run"
        original_run.mkdir(parents=True)
        replacement = self.root / "replacement"
        replacement_run = replacement / "run"
        replacement_run.mkdir(parents=True)
        moved_ancestor = self.root / "moved-ancestor"
        from writing_master import failure_cases
        original_write = failure_cases.atomic_write_bytes_at
        swapped = False

        def retarget_before_write(directory_fd, name, value):
            nonlocal swapped
            if not swapped:
                ancestor.rename(moved_ancestor)
                ancestor.symlink_to(replacement, target_is_directory=True)
                swapped = True
            return original_write(directory_fd, name, value)

        with patch("writing_master.failure_cases.atomic_write_bytes_at", side_effect=retarget_before_write):
            write_snapshot(original_run, tags=["headings"], path=self.library)

        self.assertTrue((moved_ancestor / "run" / SNAPSHOT_FILE).is_file())
        self.assertFalse((replacement_run / SNAPSHOT_FILE).exists())

    def contract(self, reader_goal="知道广告判断不应成为标题"):
        return {
            "title": "Synthetic Contract",
            "reader_goal": reader_goal,
            "deliverable": ["final.md"],
            "required_content": ["读者问题"],
            "reader_visible": ["结论"],
            "internal_constraints": ["广告判断内部保存"],
            "persona_voice": "natural-default",
            "acceptance_criteria": ["标题服务读者"],
            "failure_case_rules": ["选择 active 案例"],
            "open_items": [],
        }

    def test_spec_is_write_once_idempotent_and_verifiable_by_expected_hash(self):
        result = save_spec(self.run, self.contract())
        with patch("writing_master.run_spec.atomic_write_bytes_at") as writer:
            self.assertEqual(save_spec(self.run, self.contract()), result)
        writer.assert_not_called()
        self.assertEqual(result["sha256"], spec_sha256(self.run))
        self.assertEqual(verify_spec(self.run, expected_sha256=result["sha256"]), result)
        self.assertIn("## 内部执行约束", (self.run / "spec.md").read_text(encoding="utf-8"))

        before = (self.run / "spec.md").read_bytes()
        with self.assertRaises(SpecError) as captured:
            save_spec(self.run, self.contract("另一个目标"), version=1)
        self.assertEqual(captured.exception.code, "conflict")
        self.assertEqual((self.run / "spec.md").read_bytes(), before)

        with self.assertRaises(SpecError) as captured:
            verify_spec(self.run, expected_sha256="0" * 64)
        self.assertEqual(captured.exception.code, "hash_mismatch")

    def test_initial_spec_version_must_start_at_one(self):
        with self.assertRaises(SpecError) as captured:
            save_spec(self.run, self.contract(), version=2)
        self.assertEqual(captured.exception.code, "conflict")
        self.assertFalse((self.run / "spec.md").exists())

    def test_new_spec_version_preserves_immutable_history_and_updates_current(self):
        first = save_spec(self.run, self.contract(), version=1)
        first_bytes = (self.run / "spec-v1.md").read_bytes()
        second = save_spec(self.run, self.contract("理解新版本合同"), version=2)

        self.assertEqual((self.run / "spec-v1.md").read_bytes(), first_bytes)
        self.assertEqual((self.run / "spec-v2.md").read_bytes(), (self.run / "spec.md").read_bytes())
        self.assertNotEqual(first["sha256"], second["sha256"])
        metadata = json.loads((self.run / "spec-metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["current_version"], 2)
        self.assertEqual(metadata["current_sha256"], second["sha256"])
        self.assertEqual(verify_spec(self.run, version=1)["sha256"], first["sha256"])

    def test_spec_publish_recovers_after_interrupted_multi_file_update(self):
        from writing_master import run_spec
        original_write = run_spec.atomic_write_bytes_at
        calls = 0

        def fail_initial_metadata(directory_fd, name, value):
            nonlocal calls
            calls += 1
            if name == "spec-metadata.json":
                raise OSError("synthetic metadata failure")
            return original_write(directory_fd, name, value)

        with patch("writing_master.run_spec.atomic_write_bytes_at", side_effect=fail_initial_metadata):
            with self.assertRaises(OSError):
                save_spec(self.run, self.contract())
        self.assertGreaterEqual(calls, 3)
        first = save_spec(self.run, self.contract())
        self.assertEqual(verify_spec(self.run), first)

        def fail_version_metadata(directory_fd, name, value):
            if name == "spec-metadata.json":
                raise OSError("synthetic version metadata failure")
            return original_write(directory_fd, name, value)

        with patch("writing_master.run_spec.atomic_write_bytes_at", side_effect=fail_version_metadata):
            with self.assertRaises(OSError):
                save_spec(self.run, self.contract("恢复第二版"), version=2)
        second = save_spec(self.run, self.contract("恢复第二版"), version=2)
        self.assertEqual(verify_spec(self.run), second)
        self.assertEqual(verify_spec(self.run, version=1)["sha256"], first["sha256"])

    def test_spec_detects_current_history_and_metadata_tampering(self):
        result = save_spec(self.run, self.contract())
        for filename, replacement in (
            ("spec.md", b"tampered current"),
            ("spec-v1.md", b"tampered history"),
            ("spec-metadata.json", b"[]"),
        ):
            with self.subTest(filename=filename):
                isolated = self.root / filename.replace(".", "-")
                isolated.mkdir()
                save_spec(isolated, self.contract())
                (isolated / filename).write_bytes(replacement)
                with self.assertRaises(SpecError):
                    verify_spec(isolated, expected_sha256=result["sha256"])

    def test_spec_rejects_final_symlinks_without_touching_target(self):
        for filename in ("spec.md", "spec-v1.md", "spec-metadata.json"):
            with self.subTest(filename=filename):
                run = self.root / filename.replace(".", "-")
                run.mkdir()
                outside = self.root / f"outside-{filename}"
                outside.write_text("outside", encoding="utf-8")
                (run / filename).symlink_to(outside)
                with self.assertRaises(SpecError) as captured:
                    save_spec(run, self.contract())
                self.assertEqual(captured.exception.code, "path_escape")
                self.assertEqual(outside.read_text(encoding="utf-8"), "outside")

    def test_spec_keeps_anchored_run_when_ancestor_is_retargeted(self):
        ancestor = self.root / "spec-ancestor"
        original_run = ancestor / "run"
        original_run.mkdir(parents=True)
        replacement = self.root / "spec-replacement"
        replacement_run = replacement / "run"
        replacement_run.mkdir(parents=True)
        moved_ancestor = self.root / "moved-spec-ancestor"
        from writing_master import run_spec
        original_write = run_spec.atomic_write_bytes_at
        swapped = False

        def retarget_before_write(directory_fd, name, value):
            nonlocal swapped
            if not swapped:
                ancestor.rename(moved_ancestor)
                ancestor.symlink_to(replacement, target_is_directory=True)
                swapped = True
            return original_write(directory_fd, name, value)

        with patch("writing_master.run_spec.atomic_write_bytes_at", side_effect=retarget_before_write):
            result = save_spec(original_run, self.contract())

        anchored = moved_ancestor / "run"
        self.assertEqual(hashlib.sha256((anchored / "spec.md").read_bytes()).hexdigest(), result["sha256"])
        self.assertFalse((replacement_run / "spec.md").exists())


if __name__ == "__main__":
    unittest.main()
