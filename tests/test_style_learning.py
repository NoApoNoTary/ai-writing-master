from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import json
import multiprocessing
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import writing_master.personal_context as personal_context
from writing_master.personal_context import (
    ContextError,
    ContextStore,
    canonical_json_bytes,
    canonical_sha256,
    empty_style,
    validate_snapshot,
    validate_style,
)


def candidate(*, guidance: str = "先给结论", evidence: list[dict] | None = None) -> dict:
    return {
        "source": {
            "task_id": "TASK-N",
            "baseline": {"path": "draft-v1.md", "sha256": "a" * 64},
            "edited": {"path": "final.md", "sha256": "b" * 64},
        },
        "evidence": evidence or [{"kind": "snippet", "before": "修改前", "after": "修改后"}],
        "rule": {
            "dimension": "expression",
            "guidance": guidance,
            "scope": {"kind": "global", "value": ""},
        },
        "proposal": {"model": "MODEL", "prompt": "prompt"},
    }


def _concurrent_propose(home: str, value: dict, barrier, results) -> None:
    try:
        barrier.wait(3)
        observation = ContextStore(home).propose_style_observation(value)
        results.put(("ok", observation["observation_id"]))
    except ContextError as error:
        results.put(("error", error.code))


def _concurrent_decide(home: str, observation_id: str, decision: str, barrier, results) -> None:
    try:
        barrier.wait(3)
        result = ContextStore(home).decide_style_observation(observation_id, decision=decision)
        results.put(("ok", result["observation"]["status"]))
    except ContextError as error:
        results.put(("error", error.code))


class StyleLearningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "home"
        self.store = ContextStore(self.home)
        self.store.initialize()

    def assert_error(self, code: str, call) -> None:
        with self.assertRaises(ContextError) as caught:
            call()
        self.assertEqual(code, caught.exception.code)

    def run_directory(self, task_id: str) -> Path:
        run = Path(self.temp.name) / task_id
        run.mkdir()
        (run / "status.json").write_text(json.dumps({"task_id": task_id}), encoding="utf-8")
        return run

    def observation_path(self, observation_id: str) -> Path:
        return self.home / "personal-context" / "style-observations" / f"{observation_id}.json"

    def test_goal_a_empty_style_bytes_and_hash_stay_canonical(self):
        self.assertEqual(self.store.read_style(), empty_style())
        self.assertEqual(self.store.style_path.read_bytes(), canonical_json_bytes(empty_style()))

    def test_candidate_contract_normalizes_nfc_and_accepts_both_evidence_kinds(self):
        value = candidate(
            guidance="Cafe\u0301",
            evidence=[
                {"kind": "snippet", "before": "旧句", "after": "新句"},
                {"kind": "diff_ref", "path": "revision-report.yaml", "ref": "changes[0]"},
            ],
        )
        value["source"]["task_id"] = "TA\u0301SK"
        value["proposal"] = {"model": "MO\u0301DEL", "prompt": "pro\u0301mpt"}
        observation = self.store.propose_style_observation(value)
        self.assertEqual(observation["rule"]["guidance"], "Café")
        self.assertEqual(observation["source"]["task_id"], "TÁSK")
        self.assertEqual(observation["proposal"], {"model": "MÓDEL", "prompt": "prómpt"})
        self.assertEqual([item["kind"] for item in observation["evidence"]], ["snippet", "diff_ref"])

        invalid = []
        extra = candidate()
        extra["extra"] = True
        invalid.append(extra)
        same_hash = candidate()
        same_hash["source"]["edited"]["sha256"] = "a" * 64
        invalid.append(same_hash)
        uppercase_hash = candidate()
        uppercase_hash["source"]["baseline"]["sha256"] = "A" * 64
        invalid.append(uppercase_hash)
        unsafe_path = candidate()
        unsafe_path["source"]["baseline"]["path"] = "../draft.md"
        invalid.append(unsafe_path)
        bad_dimension = candidate()
        bad_dimension["rule"]["dimension"] = "voice"
        invalid.append(bad_dimension)
        bad_global_scope = candidate()
        bad_global_scope["rule"]["scope"]["value"] = "wechat"
        invalid.append(bad_global_scope)
        bad_platform_scope = candidate()
        bad_platform_scope["rule"]["scope"] = {"kind": "platform", "value": ""}
        invalid.append(bad_platform_scope)
        same_snippet = candidate()
        same_snippet["evidence"] = [{"kind": "snippet", "before": "same", "after": "same"}]
        invalid.append(same_snippet)
        unsafe_diff = candidate()
        unsafe_diff["evidence"] = [{"kind": "diff_ref", "path": "../diff", "ref": "x"}]
        invalid.append(unsafe_diff)
        for bad in invalid:
            with self.subTest(bad=bad):
                self.assert_error("invalid_input", lambda bad=bad: self.store.propose_style_observation(bad))

    def test_propose_has_stable_id_dual_hash_and_is_idempotent(self):
        value = candidate()
        first = self.store.propose_style_observation(value)
        expected_content_hash = canonical_sha256(value)
        self.assertEqual(first["observation_id"], "observation-" + expected_content_hash[:16])
        self.assertEqual(first["revision"], 1)
        self.assertEqual(first["status"], "proposed")
        self.assertEqual(first["content_sha256"], expected_content_hash)
        self.assertEqual(
            first["observation_sha256"],
            canonical_sha256({key: item for key, item in first.items() if key != "observation_sha256"}),
        )
        self.assertEqual(first, self.store.propose_style_observation(deepcopy(value)))
        self.assertEqual(first, self.store.read_style_observation(first["observation_id"]))

    def test_observation_directory_and_file_symlinks_are_rejected(self):
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        observations = self.home / "personal-context" / "style-observations"
        observations.symlink_to(outside, target_is_directory=True)
        self.assert_error("path_escape", lambda: self.store.propose_style_observation(candidate()))

        second_home = Path(self.temp.name) / "second-home"
        second = ContextStore(second_home)
        second.initialize()
        value = candidate()
        observation_id = "observation-" + canonical_sha256(value)[:16]
        observation_dir = second_home / "personal-context" / "style-observations"
        observation_dir.mkdir()
        target = outside / "observation.json"
        target.write_text("{}", encoding="utf-8")
        (observation_dir / f"{observation_id}.json").symlink_to(target)
        self.assert_error("path_escape", lambda: second.propose_style_observation(value))
        self.assert_error("path_escape", lambda: second.list_style_observations())

    def test_list_is_sorted_and_filters_status(self):
        observations = [
            self.store.propose_style_observation(candidate(guidance=guidance))
            for guidance in ("C", "A", "B")
        ]
        self.store.decide_style_observation(observations[0]["observation_id"], decision="accepted")
        self.store.decide_style_observation(observations[1]["observation_id"], decision="rejected")
        listed = self.store.list_style_observations()
        self.assertEqual(
            [item["observation_id"] for item in listed],
            sorted(item["observation_id"] for item in observations),
        )
        self.assertEqual(
            [item["status"] for item in self.store.list_style_observations(status="accepted")],
            ["accepted"],
        )
        self.assertEqual(
            [item["status"] for item in self.store.list_style_observations(status="rejected")],
            ["rejected"],
        )
        self.assertEqual(
            [item["status"] for item in self.store.list_style_observations(status="proposed")],
            ["proposed"],
        )
        self.assert_error("invalid_input", lambda: self.store.list_style_observations(status="unknown"))

    def test_decisions_are_terminal_idempotent_and_traceable(self):
        proposed = self.store.propose_style_observation(candidate())
        result = self.store.decide_style_observation(proposed["observation_id"], decision="accepted")
        accepted = result["observation"]
        self.assertEqual((accepted["revision"], accepted["status"]), (2, "accepted"))
        self.assertEqual(accepted["decision_provenance"], {"kind": "user_confirmed"})
        self.assertIsNotNone(datetime.fromisoformat(accepted["decided_at"]))
        self.assertEqual(
            accepted["observation_sha256"],
            canonical_sha256({key: item for key, item in accepted.items() if key != "observation_sha256"}),
        )
        self.assertEqual(
            result,
            self.store.decide_style_observation(proposed["observation_id"], decision="accepted"),
        )
        self.assert_error(
            "revision_conflict",
            lambda: self.store.decide_style_observation(proposed["observation_id"], decision="rejected"),
        )
        self.assert_error(
            "invalid_input",
            lambda: self.store.decide_style_observation(proposed["observation_id"], decision=[]),
        )

    def test_proposed_and_rejected_observations_do_not_change_style(self):
        proposed = self.store.propose_style_observation(candidate())
        self.assertEqual(self.store.read_style(), empty_style())
        self.store.decide_style_observation(proposed["observation_id"], decision="rejected")
        self.assertEqual(self.store.read_style(), empty_style())

    def test_accepted_observations_build_sorted_traceable_style(self):
        accepted = [
            self.store.propose_style_observation(candidate(guidance=guidance))
            for guidance in ("second", "first")
        ]
        rejected = self.store.propose_style_observation(candidate(guidance="rejected"))
        proposed = self.store.propose_style_observation(candidate(guidance="proposed"))
        self.store.decide_style_observation(accepted[1]["observation_id"], decision="accepted")
        self.store.decide_style_observation(rejected["observation_id"], decision="rejected")
        self.store.decide_style_observation(accepted[0]["observation_id"], decision="accepted")
        style = self.store.read_style()
        self.assertEqual((style["status"], style["revision"]), ("ready", 2))
        self.assertEqual([rule["rule_id"] for rule in style["rules"]], sorted(rule["rule_id"] for rule in style["rules"]))
        terminal = {
            item["observation_id"]: item
            for item in self.store.list_style_observations(status="accepted")
        }
        self.assertEqual(
            {rule["observation_refs"][0]["observation_id"] for rule in style["rules"]},
            set(terminal),
        )
        for rule in style["rules"]:
            reference = rule["observation_refs"][0]
            self.assertEqual(reference["revision"], 2)
            self.assertEqual(reference["observation_sha256"], terminal[reference["observation_id"]]["observation_sha256"])
        self.assertEqual(
            style["updated_at"],
            max((item["decided_at"] for item in terminal.values()), key=datetime.fromisoformat),
        )
        self.assertEqual(
            style["content_sha256"],
            canonical_sha256({"rules": style["rules"], "provenance": style["provenance"]}),
        )
        excluded = {rejected["observation_id"], proposed["observation_id"]}
        self.assertTrue(excluded.isdisjoint(terminal))

    def test_interrupted_style_write_reconciles_on_read_and_snapshot(self):
        original_write = personal_context.atomic_write_json_at

        def fail_ready_style(directory_fd, name, value):
            if name == personal_context.STYLE_FILE and value.get("status") == "ready":
                raise RuntimeError("synthetic process interruption")
            return original_write(directory_fd, name, value)

        first = self.store.propose_style_observation(candidate(guidance="first"))
        with mock.patch.object(personal_context, "atomic_write_json_at", side_effect=fail_ready_style):
            with self.assertRaises(RuntimeError):
                self.store.decide_style_observation(first["observation_id"], decision="accepted")
        self.assertEqual(self.store.read_style()["revision"], 1)

        second = self.store.propose_style_observation(candidate(guidance="second"))
        with mock.patch.object(personal_context, "atomic_write_json_at", side_effect=fail_ready_style):
            with self.assertRaises(RuntimeError):
                self.store.decide_style_observation(second["observation_id"], decision="accepted")
        run = self.run_directory("TASK-RECONCILE")
        self.assertEqual(self.store.create_snapshot(run)["style"]["revision"], 2)

    def test_conflicting_decide_reconciles_before_reporting_conflict(self):
        proposed = self.store.propose_style_observation(candidate())
        original_write = personal_context.atomic_write_json_at

        def fail_ready_style(directory_fd, name, value):
            if name == personal_context.STYLE_FILE and value.get("status") == "ready":
                raise RuntimeError("synthetic process interruption")
            return original_write(directory_fd, name, value)

        with mock.patch.object(personal_context, "atomic_write_json_at", side_effect=fail_ready_style):
            with self.assertRaises(RuntimeError):
                self.store.decide_style_observation(proposed["observation_id"], decision="accepted")
        self.assertEqual(json.loads(self.store.style_path.read_text(encoding="utf-8"))["status"], "empty")
        self.assert_error(
            "revision_conflict",
            lambda: self.store.decide_style_observation(proposed["observation_id"], decision="rejected"),
        )
        self.assertEqual(json.loads(self.store.style_path.read_text(encoding="utf-8"))["status"], "ready")

    def test_corrupt_style_or_observation_is_not_masked(self):
        proposed = self.store.propose_style_observation(candidate())
        self.store.decide_style_observation(proposed["observation_id"], decision="accepted")
        style_path = self.store.style_path
        valid_style = style_path.read_bytes()

        style = json.loads(valid_style)
        style["content_sha256"] = "0" * 64
        style_path.write_text(json.dumps(style), encoding="utf-8")
        self.assert_error("hash_mismatch", lambda: self.store.read_style())
        self.assertNotEqual(style_path.read_bytes(), valid_style)
        style_path.write_bytes(valid_style)

        observation_path = self.observation_path(proposed["observation_id"])
        observation = json.loads(observation_path.read_text(encoding="utf-8"))
        observation["rule"]["guidance"] = "tampered"
        observation_path.write_text(json.dumps(observation), encoding="utf-8")
        before = style_path.read_bytes()
        self.assert_error("hash_mismatch", lambda: self.store.read_style())
        self.assertEqual(style_path.read_bytes(), before)

    def test_missing_or_changed_accepted_observation_preserves_last_style(self):
        proposed = self.store.propose_style_observation(candidate())
        accepted = self.store.decide_style_observation(proposed["observation_id"], decision="accepted")["observation"]
        style_path = self.store.style_path
        before = style_path.read_bytes()
        observation_path = self.observation_path(accepted["observation_id"])
        observation_path.unlink()
        self.assert_error("hash_mismatch", lambda: self.store.read_style())
        self.assertEqual(style_path.read_bytes(), before)

        changed = deepcopy(accepted)
        changed["decided_at"] = "2099-01-01T00:00:00+00:00"
        changed["observation_sha256"] = canonical_sha256(
            {key: item for key, item in changed.items() if key != "observation_sha256"}
        )
        observation_path.write_text(json.dumps(changed), encoding="utf-8")
        self.assert_error("hash_mismatch", lambda: self.store.read_style())
        self.assertEqual(style_path.read_bytes(), before)

    def test_task_n_snapshot_is_unchanged_and_task_n_plus_one_gets_only_accepted(self):
        run_one = self.run_directory("TASK-1")
        run_two = self.run_directory("TASK-2")
        first = self.store.create_snapshot(run_one)
        first_bytes = (run_one / personal_context.SNAPSHOT_FILE).read_bytes()
        accepted = self.store.propose_style_observation(candidate(guidance="accepted"))
        rejected = self.store.propose_style_observation(candidate(guidance="rejected"))
        self.store.propose_style_observation(candidate(guidance="proposed"))
        self.store.decide_style_observation(accepted["observation_id"], decision="accepted")
        self.store.decide_style_observation(rejected["observation_id"], decision="rejected")
        self.assertEqual(first, self.store.create_snapshot(run_one))
        self.assertEqual((run_one / personal_context.SNAPSHOT_FILE).read_bytes(), first_bytes)
        second = self.store.create_snapshot(run_two)
        self.assertEqual((first["style"]["status"], second["style"]["status"]), ("empty", "ready"))
        self.assertEqual(second["style"]["revision"], 1)
        self.assertEqual(
            second["style"]["content"]["rules"][0]["observation_refs"][0]["observation_id"],
            accepted["observation_id"],
        )

    def test_frozen_ready_style_tampering_and_bad_shape_use_stable_errors(self):
        proposed = self.store.propose_style_observation(candidate())
        self.store.decide_style_observation(proposed["observation_id"], decision="accepted")
        run = self.run_directory("TASK-FROZEN")
        snapshot = self.store.create_snapshot(run)
        tampered = deepcopy(snapshot)
        tampered["style"]["content"]["rules"][0]["guidance"] = "tampered"
        self.assert_error("hash_mismatch", lambda: validate_snapshot(tampered))
        malformed = deepcopy(snapshot)
        malformed["style"]["content"] = []
        self.assert_error("schema_unsupported", lambda: validate_snapshot(malformed))

        for invalid_reference in (
            {"observation_id": [], "revision": 2, "observation_sha256": "0" * 64},
            {"observation_id": proposed["observation_id"], "revision": 2.0, "observation_sha256": "0" * 64},
        ):
            with self.subTest(invalid_reference=invalid_reference):
                invalid_style = self.store.read_style()
                invalid_style["rules"][0]["observation_refs"] = [invalid_reference]
                self.assert_error("schema_unsupported", lambda invalid_style=invalid_style: validate_style(invalid_style))

    def test_concurrent_propose_and_opposite_decisions_are_serialized(self):
        context = multiprocessing.get_context("fork")
        barrier = context.Barrier(2)
        results = context.Queue()
        processes = [
            context.Process(target=_concurrent_propose, args=(str(self.home), candidate(), barrier, results))
            for _ in range(2)
        ]
        for process in processes:
            process.start()
        for process in processes:
            process.join(5)
            self.assertEqual(process.exitcode, 0)
        outcomes = [results.get(timeout=2) for _ in processes]
        self.assertEqual([outcome[0] for outcome in outcomes], ["ok", "ok"])
        self.assertEqual(len({outcome[1] for outcome in outcomes}), 1)
        observation_id = outcomes[0][1]

        barrier = context.Barrier(2)
        results = context.Queue()
        processes = [
            context.Process(
                target=_concurrent_decide,
                args=(str(self.home), observation_id, decision, barrier, results),
            )
            for decision in ("accepted", "rejected")
        ]
        for process in processes:
            process.start()
        for process in processes:
            process.join(5)
            self.assertEqual(process.exitcode, 0)
        outcomes = [results.get(timeout=2) for _ in processes]
        self.assertCountEqual([outcome[0] for outcome in outcomes], ["ok", "error"])
        self.assertEqual([outcome[1] for outcome in outcomes if outcome[0] == "error"], ["revision_conflict"])


if __name__ == "__main__":
    unittest.main()
