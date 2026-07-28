from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from writing_master.personal_context import ContextError, ContextStore, empty_style


class StyleLearningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "home"
        self.store = ContextStore(self.home)
        self.store.initialize()

    def candidate(self, *, guidance="先给结论"):
        return {
            "source": {
                "task_id": "TASK-N",
                "baseline": {"path": "draft-v1.md", "sha256": "a" * 64},
                "edited": {"path": "final.md", "sha256": "b" * 64},
            },
            "evidence": [{"kind": "snippet", "before": "修改前", "after": "修改后"}],
            "rule": {"dimension": "expression", "guidance": guidance, "scope": {"kind": "global", "value": ""}},
            "proposal": {"model": "MODEL", "prompt": "prompt"},
        }

    def assert_error(self, code, call):
        with self.assertRaises(ContextError) as caught:
            call()
        self.assertEqual(code, caught.exception.code)

    def test_empty_style_hash_is_stable_and_proposed_is_idempotent(self):
        self.assertEqual(self.store.read_style(), empty_style())
        first = self.store.propose_style_observation(self.candidate(guidance="Cafe\u0301"))
        second = self.store.propose_style_observation(self.candidate(guidance="Café"))
        self.assertEqual(first, second)
        self.assertEqual("Café", first["rule"]["guidance"])
        self.assertEqual(1, first["revision"])
        self.assertEqual(empty_style(), self.store.read_style())

    def test_decisions_build_style_and_are_immutable(self):
        accepted = self.store.propose_style_observation(self.candidate())
        rejected = self.store.propose_style_observation(self.candidate(guidance="短句"))
        result = self.store.decide_style_observation(accepted["observation_id"], decision="accepted")
        self.assertEqual(2, result["observation"]["revision"])
        self.assertEqual("ready", result["style"]["status"])
        self.assertEqual(1, result["style"]["revision"])
        self.assertEqual(result, self.store.decide_style_observation(accepted["observation_id"], decision="accepted"))
        self.store.decide_style_observation(rejected["observation_id"], decision="rejected")
        self.assertEqual(1, self.store.read_style()["revision"])
        self.assert_error("revision_conflict", lambda: self.store.decide_style_observation(accepted["observation_id"], decision="rejected"))

    def test_reconcile_and_candidate_validation(self):
        observation = self.store.propose_style_observation(self.candidate())
        self.store.decide_style_observation(observation["observation_id"], decision="accepted")
        style_path = self.home / "personal-context" / "style-profile.json"
        style_path.write_text(json.dumps(empty_style()), encoding="utf-8")
        self.assertEqual("ready", self.store.read_style()["status"])
        bad = self.candidate()
        bad["source"]["baseline"]["path"] = "../draft.md"
        self.assert_error("invalid_input", lambda: self.store.propose_style_observation(bad))

    def test_snapshot_freezes_style_before_later_acceptance(self):
        run_one = Path(self.temp.name) / "run-one"
        run_two = Path(self.temp.name) / "run-two"
        for run, task_id in ((run_one, "TASK-1"), (run_two, "TASK-2")):
            run.mkdir()
            (run / "status.json").write_text(json.dumps({"task_id": task_id}), encoding="utf-8")
        first = self.store.create_snapshot(run_one)
        observation = self.store.propose_style_observation(self.candidate())
        self.store.decide_style_observation(observation["observation_id"], decision="accepted")
        self.assertEqual(first, self.store.create_snapshot(run_one))
        self.assertEqual("empty", first["style"]["status"])
        self.assertEqual("ready", self.store.create_snapshot(run_two)["style"]["status"])


if __name__ == "__main__":
    unittest.main()
