import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from writing_master import handoff


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.run = Path(self.temporary.name)
        (self.run / "status.json").write_text(json.dumps({
            "task_id": "TASK-001", "mode": "deep", "execution": "multi_agent",
            "status": "in_progress",
        }), encoding="utf-8")
        (self.run / "brief.md").write_text("brief", encoding="utf-8")

    def tearDown(self):
        self.temporary.cleanup()

    def prepare(self, role="researcher", phase="research", inputs=None, outputs=None):
        return handoff.prepare(
            self.run, to_role=role, phase=phase, objective="objective", decision_to_inform="decision",
            inputs=inputs or ["brief.md"], write_scope=outputs or ["output.md"], done_criteria=["done"],
        )

    def finish(self, prepared, *, status="completed", bad_hash=False, failure_type=None, actual_paths=False):
        manifest = prepared["manifest"]
        state = json.loads((prepared["attempt_dir"] / "state.json").read_text(encoding="utf-8"))
        outputs = []
        if status == "completed":
            for logical in manifest["expected_outputs"]:
                path = self.run / manifest["output_root"] / logical
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f"{logical} content", encoding="utf-8")
                digest = "0" * 64 if bad_hash else handoff.sha256_file(path)
                outputs.append(
                    {"logical_name": logical, "path": f"outputs/{logical}", "sha256": digest}
                    if actual_paths else {"path": logical, "sha256": digest}
                )
        result = {
            "schema_version": 1, "handoff_id": manifest["handoff_id"], "attempt": manifest["attempt"],
            "agent_ref": state.get("agent_ref", "fake-host-agent"), "status": status, "outputs": outputs,
            "blocking_issues": [], "summary": "done", "completed_at": "2026-07-27T00:00:00+00:00",
        }
        if failure_type:
            result["failure_type"] = failure_type
        (self.run / manifest["result_path"]).write_text(json.dumps(result), encoding="utf-8")

    def complete_stage(self, role, phase, inputs, outputs):
        prepared = self.prepare(role, phase, inputs, outputs)
        handoff.mark_running(self.run, f"fake-{role}")
        self.finish(prepared, actual_paths=True)
        handoff.complete(self.run)
        return prepared

    def test_fake_host_full_chain_and_new_process_resume(self):
        research = self.complete_stage("researcher", "research", ["brief.md"], ["claims.yaml", "sources.yaml"])
        strategy = self.complete_stage("editorial_strategist", "strategy", ["claims.yaml", "sources.yaml"], ["outline.md"])
        draft = self.complete_stage("writer", "draft", ["outline.md"], ["draft-v1.md"])
        review = self.complete_stage("auditor", "review", ["draft-v1.md"], ["review-report.yaml"])
        revision = self.complete_stage("writer", "revision", ["draft-v1.md", "review-report.yaml"], ["final.md"])

        self.assertEqual((self.run / "final.md").read_text(encoding="utf-8"), "final.md content")
        self.assertTrue((research["attempt_dir"] / "outputs" / "claims.yaml").is_file())
        self.assertEqual(handoff.show(self.run)["effective_status"], "completed")
        code = "from writing_master.handoff import show; import json,sys; print(json.dumps(show(sys.argv[1])))"
        result = subprocess.run([os.sys.executable, "-c", code, str(self.run)], text=True, capture_output=True, check=True)
        self.assertEqual(json.loads(result.stdout)["handoff"]["handoff_id"], revision["manifest"]["handoff_id"])
        self.assertEqual(strategy["manifest"]["allowed_inputs"][0]["path"], "claims.yaml")
        self.assertEqual(draft["manifest"]["to_role"], "writer")
        self.assertEqual(review["manifest"]["to_role"], "auditor")

    def test_missing_or_bad_output_blocks_progress_and_preserves_root(self):
        prepared = self.prepare(outputs=["output.md"])
        handoff.mark_running(self.run, "agent")
        self.finish(prepared, bad_hash=True)
        with self.assertRaises(handoff.HandoffError):
            handoff.complete(self.run)
        self.assertFalse((self.run / "output.md").exists())
        self.assertEqual(handoff.show(self.run)["handoff"]["status"], "failed")

    def test_missing_or_malformed_result_marks_running_attempt_failed(self):
        prepared = self.prepare()
        handoff.mark_running(self.run, "agent")
        with self.assertRaises(handoff.HandoffError):
            handoff.complete(self.run)
        shown = handoff.show(self.run)
        self.assertEqual(shown["handoff"]["status"], "failed")
        self.assertIn("output_validation", shown["state_reason"])

        retry = self.prepare()
        handoff.mark_running(self.run, "agent-2")
        (self.run / retry["manifest"]["result_path"]).write_text("{", encoding="utf-8")
        with self.assertRaises(handoff.HandoffError):
            handoff.complete(self.run)
        self.assertEqual(handoff.show(self.run)["handoff"]["status"], "failed")

    def test_extra_or_symlinked_staged_outputs_are_rejected(self):
        prepared = self.prepare()
        handoff.mark_running(self.run, "agent")
        self.finish(prepared)
        output_root = self.run / prepared["manifest"]["output_root"]
        (output_root / "extra.md").write_text("unexpected", encoding="utf-8")
        with self.assertRaises(handoff.HandoffError):
            handoff.complete(self.run)
        self.assertEqual(handoff.show(self.run)["handoff"]["status"], "failed")

        retry = self.prepare()
        handoff.mark_running(self.run, "agent-2")
        self.finish(retry)
        (self.run / retry["manifest"]["output_root"] / "link.md").symlink_to(self.run / "brief.md")
        with self.assertRaises(handoff.HandoffError):
            handoff.complete(self.run)

    def test_input_change_makes_completed_handoff_effectively_stale(self):
        prepared = self.prepare()
        handoff.mark_running(self.run, "agent")
        self.finish(prepared)
        handoff.complete(self.run)
        (self.run / "brief.md").write_text("changed", encoding="utf-8")
        shown = handoff.show(self.run)
        self.assertEqual(shown["handoff"]["status"], "completed")
        self.assertEqual(shown["effective_status"], "stale")
        self.assertFalse(shown["input_fresh"])

    def test_deep_context_manifest_is_task_local_and_snapshot_tamper_is_stale(self):
        snapshot = self.run / "personal-context-snapshot.json"
        material = self.run / "context-materials" / "knowledge-synthetic.md"
        snapshot.write_text('{"task_id":"TASK-001","snapshot":"frozen"}\n', encoding="utf-8")
        material.parent.mkdir()
        material.write_text("Synthetic task-local material\n", encoding="utf-8")
        global_context = Path(self.temporary.name) / "home" / "personal-context"
        global_context.mkdir(parents=True)
        (global_context / "author-profile.json").write_text("global-only\n", encoding="utf-8")

        writer = handoff.prepare(
            self.run,
            to_role="writer",
            phase="draft",
            objective="write from frozen task context",
            decision_to_inform="draft review",
            inputs=["brief.md", "personal-context-snapshot.json", "context-materials/knowledge-synthetic.md"],
            write_scope=["draft-v1.md"],
            done_criteria=["draft exists"],
            forbidden_inputs=["parent_conversation"],
        )
        self.assertEqual(
            [item["path"] for item in writer["manifest"]["allowed_inputs"]],
            ["brief.md", "personal-context-snapshot.json", "context-materials/knowledge-synthetic.md"],
        )
        self.assertEqual(writer["manifest"]["forbidden_inputs"], ["parent_conversation"])
        self.assertNotIn(str(global_context), [item["path"] for item in writer["manifest"]["allowed_inputs"]])
        for item in writer["manifest"]["allowed_inputs"]:
            self.assertTrue(item["required"])
            self.assertEqual(item["sha256"], handoff.sha256_file(self.run / item["path"]))
        handoff.mark_running(self.run, "writer-agent")
        self.finish(writer, actual_paths=True)
        handoff.complete(self.run)

        auditor = handoff.prepare(
            self.run,
            to_role="auditor",
            phase="review",
            objective="audit from frozen task context",
            decision_to_inform="revision",
            inputs=["draft-v1.md", "personal-context-snapshot.json", "context-materials/knowledge-synthetic.md"],
            write_scope=["review-report.yaml"],
            done_criteria=["review exists"],
            forbidden_inputs=["parent_conversation"],
        )
        self.assertEqual(
            [item["path"] for item in auditor["manifest"]["allowed_inputs"]],
            ["draft-v1.md", "personal-context-snapshot.json", "context-materials/knowledge-synthetic.md"],
        )
        self.assertEqual(auditor["manifest"]["forbidden_inputs"], ["parent_conversation"])
        for item in auditor["manifest"]["allowed_inputs"]:
            self.assertTrue(item["required"])
            self.assertEqual(item["sha256"], handoff.sha256_file(self.run / item["path"]))

        snapshot.write_text('{"task_id":"TASK-001","snapshot":"tampered"}\n', encoding="utf-8")
        shown = handoff.show(self.run)
        self.assertEqual(shown["handoff"]["status"], "stale")
        self.assertEqual(shown["effective_status"], "stale")
        self.assertIn("input hash changed: personal-context-snapshot.json", shown["blocking_reasons"])

    def test_show_reports_stale_upstream_and_blocks_downstream_prepare(self):
        self.complete_stage("researcher", "research", ["brief.md"], ["claims.yaml"])
        self.complete_stage("editorial_strategist", "strategy", ["claims.yaml"], ["outline.md"])
        (self.run / "brief.md").write_text("changed", encoding="utf-8")
        shown = handoff.show(self.run)
        self.assertEqual(shown["effective_status"], "stale")
        self.assertEqual(shown["stale_handoffs"][0]["handoff"]["phase"], "research")
        with self.assertRaises(handoff.HandoffError):
            self.prepare("writer", "draft", ["outline.md"], ["draft-v1.md"])
        retry = self.prepare("researcher", "research", ["brief.md"], ["claims.yaml"])
        self.assertEqual(retry["manifest"]["attempt"], 2)

    def test_failed_retry_keeps_attempt_history(self):
        first = self.prepare()
        handoff.mark_running(self.run, "agent-1")
        self.finish(first, status="failed", failure_type="role_failure")
        self.assertEqual(handoff.complete(self.run)["state"]["status"], "failed")
        second = self.prepare()
        self.assertEqual(second["manifest"]["attempt"], 2)
        self.assertTrue((first["attempt_dir"] / "result.json").is_file())
        self.assertTrue((second["attempt_dir"] / "manifest.json").is_file())

    def test_failed_handoff_cannot_be_bypassed_by_downstream_prepare(self):
        first = self.prepare()
        handoff.mark_running(self.run, "agent")
        self.finish(first, bad_hash=True)
        with self.assertRaises(handoff.HandoffError):
            handoff.complete(self.run)
        with self.assertRaises(handoff.HandoffError):
            self.prepare("writer", "draft", ["brief.md"], ["draft-v1.md"])
        self.assertEqual(self.prepare()["manifest"]["attempt"], 2)

    def test_current_running_handoff_and_unsafe_phase_are_rejected(self):
        self.prepare()
        with self.assertRaises(handoff.HandoffError):
            self.prepare(phase="strategy")
        with self.assertRaises(handoff.HandoffError):
            self.prepare(phase="../strategy")

    def test_rejects_path_escape_symlink_and_illegal_transition(self):
        with self.assertRaises(handoff.HandoffError):
            self.prepare(inputs=["../outside.md"])
        outside = self.run.parent / "outside.md"
        outside.write_text("outside", encoding="utf-8")
        (self.run / "linked.md").symlink_to(outside)
        with self.assertRaises(handoff.HandoffError):
            self.prepare(inputs=["linked.md"])
        prepared = self.prepare()
        handoff.mark_running(self.run, "agent")
        with self.assertRaises(handoff.HandoffError):
            handoff.mark_running(self.run, "agent-again")

    def test_corrupt_json_and_manifest_hash_mismatch_are_rejected(self):
        prepared = self.prepare()
        original_state = (prepared["attempt_dir"] / "state.json").read_text(encoding="utf-8")
        (prepared["attempt_dir"] / "state.json").write_text("{", encoding="utf-8")
        with self.assertRaises(handoff.HandoffError):
            handoff.show(self.run)
        (prepared["attempt_dir"] / "state.json").write_text(original_state, encoding="utf-8")
        status = json.loads((self.run / "status.json").read_text(encoding="utf-8"))
        status.pop("current_handoff")
        handoff.atomic_write_json(self.run / "status.json", status)
        prepared = self.prepare(phase="other")
        state = json.loads((prepared["attempt_dir"] / "state.json").read_text(encoding="utf-8"))
        state["manifest_sha256"] = "0" * 64
        handoff.atomic_write_json(prepared["attempt_dir"] / "state.json", state)
        # Point status at this valid JSON state with an invalid manifest checksum.
        status = json.loads((self.run / "status.json").read_text(encoding="utf-8"))
        status["current_handoff"]["path"] = prepared["attempt_dir"].relative_to(self.run).as_posix()
        handoff.atomic_write_json(self.run / "status.json", status)
        with self.assertRaises(handoff.HandoffError):
            handoff.show(self.run)

    def test_atomic_write_failure_keeps_previous_json(self):
        target = self.run / "state.json"
        target.write_text('{"old": true}\n', encoding="utf-8")
        with patch("writing_master.handoff.os.replace", side_effect=OSError("interrupted")):
            with self.assertRaises(OSError):
                handoff.atomic_write_json(target, {"new": True})
        self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"old": True})

    def test_interrupted_prepare_does_not_block_retry(self):
        with patch("writing_master.handoff._write_state", side_effect=OSError("interrupted")):
            with self.assertRaises(OSError):
                self.prepare()
        retry = self.prepare()
        self.assertEqual(retry["manifest"]["attempt"], 2)

    def test_upstream_stale_reason_is_kept_when_current_handoff_failed(self):
        self.complete_stage("researcher", "research", ["brief.md"], ["claims.yaml"])
        self.complete_stage("editorial_strategist", "strategy", ["claims.yaml"], ["outline.md"])
        failed = self.prepare("writer", "draft", ["outline.md"], ["draft-v1.md"])
        handoff.mark_running(self.run, "writer")
        self.finish(failed, bad_hash=True)
        with self.assertRaises(handoff.HandoffError):
            handoff.complete(self.run)
        (self.run / "brief.md").write_text("changed", encoding="utf-8")
        shown = handoff.show(self.run)
        self.assertTrue(any("output_validation" in reason for reason in shown["blocking_reasons"]))
        self.assertTrue(any("stale research/researcher" in reason for reason in shown["blocking_reasons"]))
        with self.assertRaises(handoff.HandoffError):
            self.prepare("writer", "draft", ["outline.md"], ["draft-v1.md"])
        self.assertEqual(self.prepare("researcher", "research", ["brief.md"], ["claims.yaml"])["manifest"]["attempt"], 2)

    def test_result_agent_ref_must_match_running_state_and_show_explains_failure(self):
        prepared = self.prepare()
        handoff.mark_running(self.run, "host-agent")
        self.finish(prepared)
        result_path = self.run / prepared["manifest"]["result_path"]
        result = json.loads(result_path.read_text(encoding="utf-8"))
        result["agent_ref"] = "different-agent"
        result_path.write_text(json.dumps(result), encoding="utf-8")
        with self.assertRaises(handoff.HandoffError):
            handoff.complete(self.run)
        shown = handoff.show(self.run)
        self.assertEqual(shown["agent_ref"], "host-agent")
        self.assertIn("agent_ref", shown["blocking_reasons"][0])

    def show_in_new_process(self):
        code = "from writing_master.handoff import show; import json,sys; print(json.dumps(show(sys.argv[1])))"
        result = subprocess.run(
            [os.sys.executable, "-c", code, str(self.run)],
            text=True,
            capture_output=True,
            check=True,
        )
        return json.loads(result.stdout)

    def test_completed_result_loss_is_stale_across_new_process(self):
        prepared = self.complete_stage("researcher", "research", ["brief.md"], ["claims.yaml"])
        (self.run / prepared["manifest"]["result_path"]).unlink()

        shown = self.show_in_new_process()
        self.assertEqual(shown["handoff"]["status"], "completed")
        self.assertEqual(shown["effective_status"], "stale")
        self.assertTrue(any("missing Result" in reason for reason in shown["blocking_reasons"]))
        self.assertEqual(
            self.prepare("researcher", "research", ["brief.md"], ["claims.yaml"])["manifest"]["attempt"],
            2,
        )

    def test_promoted_output_corruption_is_stale_across_new_process(self):
        prepared = self.complete_stage("researcher", "research", ["brief.md"], ["claims.yaml"])
        (self.run / "claims.yaml").write_text("corrupted", encoding="utf-8")

        shown = self.show_in_new_process()
        self.assertEqual(shown["handoff"]["status"], "completed")
        self.assertEqual(shown["effective_status"], "stale")
        self.assertTrue(any("promoted output hash mismatch" in reason for reason in shown["blocking_reasons"]))
        self.assertTrue((self.run / prepared["manifest"]["result_path"]).is_file())

    def test_missing_promoted_output_is_stale_across_new_process(self):
        self.complete_stage("researcher", "research", ["brief.md"], ["claims.yaml"])
        (self.run / "claims.yaml").unlink()

        shown = self.show_in_new_process()
        self.assertEqual(shown["effective_status"], "stale")
        self.assertTrue(any("missing promoted output" in reason for reason in shown["blocking_reasons"]))

    def test_alternate_result_is_preserved_at_canonical_path(self):
        prepared = self.prepare()
        handoff.mark_running(self.run, "agent")
        self.finish(prepared)
        canonical = self.run / prepared["manifest"]["result_path"]
        alternate = self.run / "alternate-result.json"
        canonical.rename(alternate)

        self.assertEqual(handoff.complete(self.run, "alternate-result.json")["state"]["status"], "completed")
        self.assertTrue(canonical.is_file())
        self.assertEqual(handoff.show(self.run)["effective_status"], "completed")

    def test_prepared_attempt_resumes_across_new_process(self):
        prepared = self.prepare()
        shown = self.show_in_new_process()
        self.assertEqual(shown["handoff"]["handoff_id"], prepared["manifest"]["handoff_id"])
        self.assertEqual(shown["handoff"]["status"], "prepared")
        self.assertEqual(shown["effective_status"], "prepared")

    def test_recover_lost_running_attempt_creates_same_stage_retry(self):
        first = self.prepare()
        handoff.mark_running(self.run, "lost-agent")
        recovered = handoff.recover_lost_running(self.run, "lost-agent")

        self.assertEqual(recovered["failed"]["status"], "failed")
        self.assertEqual(recovered["failed"]["reason"], "host_failure")
        self.assertEqual(recovered["prepared"]["manifest"]["attempt"], 2)
        first_state = json.loads((first["attempt_dir"] / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(first_state["status"], "failed")
        self.assertEqual(handoff.show(self.run)["handoff"]["status"], "prepared")

        with self.assertRaises(handoff.HandoffError):
            handoff.recover_lost_running(self.run, "lost-agent")

        handoff.mark_running(self.run, "replacement-agent")
        with self.assertRaises(handoff.HandoffError):
            handoff.recover_lost_running(self.run, "other-agent")
        second = handoff.recover_lost_running(self.run, "replacement-agent")
        self.assertEqual(second["prepared"]["manifest"]["attempt"], 3)

    def test_damaged_completed_stage_blocks_downstream_and_allows_same_stage_retry(self):
        research = self.complete_stage("researcher", "research", ["brief.md"], ["claims.yaml"])
        self.complete_stage("editorial_strategist", "strategy", ["claims.yaml"], ["outline.md"])
        (self.run / research["manifest"]["output_root"] / "claims.yaml").unlink()

        shown = handoff.show(self.run)
        self.assertEqual(shown["effective_status"], "stale")
        with self.assertRaises(handoff.HandoffError):
            self.prepare("writer", "draft", ["outline.md"], ["draft-v1.md"])
        retry = self.prepare("researcher", "research", ["brief.md"], ["claims.yaml"])
        self.assertEqual(retry["manifest"]["attempt"], 2)


if __name__ == "__main__":
    unittest.main()
