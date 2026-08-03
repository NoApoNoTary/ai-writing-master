import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

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
from writing_master.run_spec import save_spec, spec_sha256


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
        self.assertIn("guardrail", snapshot)
        self.assertNotIn("source_session", snapshot)
        self.assertNotIn("root_cause", snapshot)

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

    def test_spec_is_frozen_readable_contract_with_hash(self):
        result = save_spec(self.run, {
            "title": "Synthetic Contract",
            "reader_goal": "知道广告判断不应成为标题",
            "deliverable": ["final.md"],
            "required_content": ["读者问题"],
            "reader_visible": ["结论"],
            "internal_constraints": ["广告判断内部保存"],
            "persona_voice": "natural-default",
            "acceptance_criteria": ["标题服务读者"],
            "failure_case_rules": ["选择 active 案例"],
            "open_items": [],
        })
        self.assertEqual(result["sha256"], spec_sha256(self.run))
        self.assertIn("## 内部执行约束", (self.run / "spec.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
