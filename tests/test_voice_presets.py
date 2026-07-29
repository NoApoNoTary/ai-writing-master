from __future__ import annotations

import json
from copy import deepcopy
import tempfile
import unittest
from pathlib import Path

from writing_master import handoff
from writing_master.personal_context import canonical_sha256
from writing_master.voice_presets import DEFAULT_VOICE_ID, SNAPSHOT_FILE, VoiceError, VoicePresetStore


class VoicePresetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.run = self.root / "run"
        self.run.mkdir()
        self.write_status("TASK-VOICE")
        self.registry = Path(__file__).resolve().parents[1] / "src/writing_master/voice_profiles/registry.json"

    def write_status(self, task_id: str) -> None:
        (self.run / "status.json").write_text(json.dumps({
            "task_id": task_id, "mode": "deep", "execution": "multi_agent", "status": "in_progress",
            "voice_snapshot": "pending",
        }), encoding="utf-8")

    def test_registry_and_selector_contract(self) -> None:
        store = VoicePresetStore(self.registry)
        listed = store.list_profiles()
        self.assertEqual(listed["default_id"], DEFAULT_VOICE_ID)
        self.assertEqual(
            [profile["id"] for profile in listed["profiles"]],
            ["natural-default", "clear-analytical", "conversational-observer", "sharp-commentary"],
        )
        self.assertEqual(store.resolve(None)["id"], DEFAULT_VOICE_ID)
        self.assertEqual(store.resolve("2")["id"], "clear-analytical")
        self.assertEqual(store.resolve("清晰分析")["id"], "clear-analytical")
        with self.assertRaises(VoiceError) as captured:
            store.resolve("missing")
        self.assertEqual(captured.exception.code, "unknown_voice")
        self.assertEqual(captured.exception.available, listed["profiles"])
        with self.assertRaises(VoiceError) as captured:
            store.resolve(True)
        self.assertEqual(captured.exception.code, "unknown_voice")

    def test_registry_rejects_duplicate_identity_and_profile_contract_drift(self) -> None:
        original = json.loads(self.registry.read_text(encoding="utf-8"))
        invalid = []

        duplicate = deepcopy(original)
        duplicate["profiles"][1]["id"] = duplicate["profiles"][0]["id"]
        invalid.append(duplicate)

        bad_scope = deepcopy(original)
        bad_scope["profiles"][1]["scope"] = "persona"
        invalid.append(bad_scope)

        bad_preserve = deepcopy(original)
        bad_preserve["profiles"][1]["preserve"] = ["facts"]
        invalid.append(bad_preserve)

        bad_version = deepcopy(original)
        bad_version["profiles"][1]["version"] = True
        invalid.append(bad_version)

        default_override = deepcopy(original)
        default_override["profiles"][0]["voice"]["opening"] = ["Force a temporary opening."]
        invalid.append(default_override)

        for index, document in enumerate(invalid):
            with self.subTest(index=index):
                path = self.root / f"invalid-{index}.json"
                path.write_text(json.dumps(document), encoding="utf-8")
                with self.assertRaises(VoiceError) as captured:
                    VoicePresetStore(path).read_registry()
                self.assertEqual(captured.exception.code, "registry_invalid")

    def test_snapshot_is_idempotent_but_conflicting_selection_is_rejected(self) -> None:
        store = VoicePresetStore(self.registry)
        first = store.create_snapshot(self.run, "clear-analytical")
        second = store.create_snapshot(self.run, "clear-analytical")
        self.assertEqual(first, second)
        with self.assertRaises(VoiceError) as captured:
            store.create_snapshot(self.run, "sharp-commentary")
        self.assertEqual(captured.exception.code, "snapshot_conflict")

    def test_existing_snapshot_recovers_after_registry_changes(self) -> None:
        registry = self.root / "registry.json"
        registry.write_text(self.registry.read_text(encoding="utf-8"), encoding="utf-8")
        store = VoicePresetStore(registry)
        first = store.create_snapshot(self.run, "clear-analytical")
        registry.write_text("{", encoding="utf-8")
        recovered = store.create_snapshot(self.run, "clear-analytical")
        self.assertEqual(recovered, first)
        self.assertTrue(store.verify_run(self.run)["verified"])

    def test_ready_missing_snapshot_is_not_recreated_and_legacy_is_not_backfilled(self) -> None:
        store = VoicePresetStore(self.registry)
        store.create_snapshot(self.run, "clear-analytical")
        (self.run / SNAPSHOT_FILE).unlink()
        with self.assertRaises(VoiceError) as captured:
            store.create_snapshot(self.run, "clear-analytical")
        self.assertEqual(captured.exception.code, "snapshot_missing")
        self.assertFalse((self.run / SNAPSHOT_FILE).exists())

        legacy = self.root / "legacy-no-backfill"
        legacy.mkdir()
        (legacy / "status.json").write_text(json.dumps({"task_id": "TASK-LEGACY"}), encoding="utf-8")
        self.assertEqual(store.verify_run(legacy)["voice_snapshot"], "legacy")
        result = store.create_snapshot(legacy)
        self.assertEqual(result["voice_snapshot"], "legacy")
        self.assertFalse((legacy / SNAPSHOT_FILE).exists())

    def test_existing_snapshot_does_not_mask_ready_status_tampering_or_legacy_state(self) -> None:
        store = VoicePresetStore(self.registry)
        snapshot = store.create_snapshot(self.run, "clear-analytical")
        status = json.loads((self.run / "status.json").read_text(encoding="utf-8"))
        status["voice_id"] = "sharp-commentary"
        (self.run / "status.json").write_text(json.dumps(status), encoding="utf-8")
        with self.assertRaises(VoiceError) as captured:
            store.create_snapshot(self.run, "clear-analytical")
        self.assertEqual(captured.exception.code, "hash_mismatch")

        status.update({
            "voice_id": "legacy-natural",
            "voice_profile_version": None,
            "voice_snapshot": "legacy",
            "voice_snapshot_sha256": None,
        })
        (self.run / "status.json").write_text(json.dumps(status), encoding="utf-8")
        with self.assertRaises(VoiceError) as captured:
            store.create_snapshot(self.run, "clear-analytical")
        self.assertEqual(captured.exception.code, "snapshot_conflict")
        self.assertEqual(json.loads((self.run / SNAPSHOT_FILE).read_text(encoding="utf-8")), snapshot)

    def test_pending_status_selection_is_frozen_when_cli_selector_is_omitted(self) -> None:
        (self.run / "status.json").write_text(json.dumps({
            "task_id": "TASK-VOICE",
            "voice_id": "sharp-commentary",
            "voice_snapshot": "pending",
            "voice_profile_version": None,
            "voice_snapshot_sha256": None,
            "voice_selection_source": "content_contract",
        }), encoding="utf-8")
        snapshot = VoicePresetStore(self.registry).create_snapshot(self.run)
        self.assertEqual(snapshot["profile_id"], "sharp-commentary")
        self.assertEqual(snapshot["selection_source"], "content_contract")
        self.assertEqual(VoicePresetStore(self.registry).create_snapshot(self.run), snapshot)

    def test_plain_old_tasks_are_legacy_and_partial_voice_state_is_blocked(self) -> None:
        store = VoicePresetStore(self.registry)
        legacy = self.root / "legacy-explicit-selection"
        legacy.mkdir()
        (legacy / "status.json").write_text(json.dumps({"task_id": "TASK-OLD"}), encoding="utf-8")
        with self.assertRaises(VoiceError) as captured:
            store.create_snapshot(legacy, "sharp-commentary")
        self.assertEqual(captured.exception.code, "snapshot_conflict")
        self.assertEqual(store.verify_run(legacy)["voice_snapshot"], "legacy")
        self.assertFalse((legacy / SNAPSHOT_FILE).exists())

        legacy_status = json.loads((legacy / "status.json").read_text(encoding="utf-8"))
        legacy_status["voice_id"] = "sharp-commentary"
        (legacy / "status.json").write_text(json.dumps(legacy_status), encoding="utf-8")
        with self.assertRaises(VoiceError) as captured:
            store.create_snapshot(legacy)
        self.assertEqual(captured.exception.code, "hash_mismatch")

        partial = self.root / "partial"
        partial.mkdir()
        (partial / "status.json").write_text(json.dumps({
            "task_id": "TASK-PARTIAL", "voice_id": "sharp-commentary",
        }), encoding="utf-8")
        for operation in (store.verify_run, lambda run: store.create_snapshot(run, "sharp-commentary")):
            with self.assertRaises(VoiceError) as captured:
                operation(partial)
            self.assertEqual(captured.exception.code, "snapshot_missing")
        self.assertFalse((partial / SNAPSHOT_FILE).exists())

    def test_verify_rejects_snapshot_status_and_task_tampering(self) -> None:
        store = VoicePresetStore(self.registry)
        snapshot = store.create_snapshot(self.run, "clear-analytical")
        path = self.run / SNAPSHOT_FILE

        tampered = dict(snapshot)
        tampered["profile_id"] = "sharp-commentary"
        path.write_text(json.dumps(tampered), encoding="utf-8")
        with self.assertRaises(VoiceError) as captured:
            store.verify_run(self.run)
        self.assertEqual(captured.exception.code, "hash_mismatch")

        invalid_time = dict(snapshot)
        invalid_time["created_at"] = "2026-99-99T00:00:00+00:00"
        invalid_time["snapshot_sha256"] = canonical_sha256({
            key: value for key, value in invalid_time.items() if key != "snapshot_sha256"
        })
        path.write_text(json.dumps(invalid_time), encoding="utf-8")
        with self.assertRaises(VoiceError) as captured:
            store.verify_run(self.run)
        self.assertEqual(captured.exception.code, "schema_unsupported")

        path.write_text(json.dumps(snapshot), encoding="utf-8")
        status = json.loads((self.run / "status.json").read_text(encoding="utf-8"))
        status["voice_id"] = "sharp-commentary"
        (self.run / "status.json").write_text(json.dumps(status), encoding="utf-8")
        with self.assertRaises(VoiceError) as captured:
            store.verify_run(self.run)
        self.assertEqual(captured.exception.code, "hash_mismatch")

        self.write_status("OTHER-TASK")
        with self.assertRaises(VoiceError) as captured:
            store.verify_run(self.run)
        self.assertEqual(captured.exception.code, "hash_mismatch")

    def test_legacy_and_default_registry_degradation_are_compatible(self) -> None:
        store = VoicePresetStore(self.root / "missing.json")
        degraded = store.create_snapshot(self.run)
        self.assertEqual(degraded["voice_snapshot"], "unavailable")
        self.assertEqual(store.verify_run(self.run)["voice_snapshot"], "unavailable")

        legacy = self.root / "legacy"
        legacy.mkdir()
        (legacy / "status.json").write_text(json.dumps({"task_id": "TASK-LEGACY"}), encoding="utf-8")
        verified = VoicePresetStore(self.registry).verify_run(legacy)
        self.assertEqual(verified["voice_snapshot"], "legacy")
        self.assertEqual(json.loads((legacy / "status.json").read_text(encoding="utf-8"))["voice_id"], "legacy-natural")

    def test_ancestor_and_snapshot_symlinks_are_rejected(self) -> None:
        store = VoicePresetStore(self.registry)
        store.create_snapshot(self.run)
        alias = self.root / "alias"
        alias.symlink_to(self.run, target_is_directory=True)
        with self.assertRaises(VoiceError) as captured:
            store.verify_run(alias)
        self.assertEqual(captured.exception.code, "path_escape")

        target = self.root / "target.json"
        target.write_text((self.run / SNAPSHOT_FILE).read_text(encoding="utf-8"), encoding="utf-8")
        (self.run / SNAPSHOT_FILE).unlink()
        (self.run / SNAPSHOT_FILE).symlink_to(target)
        with self.assertRaises(VoiceError) as captured:
            store.verify_run(self.run)
        self.assertEqual(captured.exception.code, "path_escape")


class VoiceHandoffTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.run = Path(self.temporary.name)
        (self.run / "status.json").write_text(json.dumps({
            "task_id": "TASK-HANDOFF", "mode": "deep", "execution": "multi_agent", "status": "in_progress",
            "voice_snapshot": "pending",
        }), encoding="utf-8")
        (self.run / "brief.md").write_text("brief", encoding="utf-8")
        VoicePresetStore().create_snapshot(self.run, "clear-analytical")

    def prepare(self, role: str, inputs: list[str] | None = None) -> dict:
        return handoff.prepare(
            self.run, to_role=role, phase={"writer": "draft", "auditor": "review", "researcher": "research", "editorial_strategist": "strategy"}[role],
            objective="objective", decision_to_inform="decision", inputs=inputs or ["brief.md"],
            write_scope=["output.md"], done_criteria=["done"],
        )

    def test_ready_voice_is_forced_for_writer_and_auditor_but_forbidden_upstream(self) -> None:
        writer = self.prepare("writer")
        self.assertIn(SNAPSHOT_FILE, [item["path"] for item in writer["manifest"]["allowed_inputs"]])
        with self.assertRaises(handoff.HandoffError):
            self.prepare("researcher", ["brief.md", SNAPSHOT_FILE])

        # A fresh run avoids the current prepared Writer attempt while checking Auditor.
        second = Path(self.temporary.name) / "second"
        second.mkdir()
        (second / "brief.md").write_text("brief", encoding="utf-8")
        (second / "status.json").write_text(json.dumps({
            "task_id": "TASK-AUDIT", "mode": "deep", "execution": "multi_agent", "status": "in_progress",
            "voice_snapshot": "pending",
        }), encoding="utf-8")
        VoicePresetStore().create_snapshot(second)
        auditor = handoff.prepare(second, to_role="auditor", phase="review", objective="objective", decision_to_inform="decision", inputs=["brief.md"], write_scope=["output.md"], done_criteria=["done"])
        self.assertIn(SNAPSHOT_FILE, [item["path"] for item in auditor["manifest"]["allowed_inputs"]])
        with self.assertRaises(handoff.HandoffError):
            handoff.prepare(second, to_role="editorial_strategist", phase="strategy", objective="objective", decision_to_inform="decision", inputs=["brief.md", SNAPSHOT_FILE], write_scope=["output.md"], done_criteria=["done"])

    def test_snapshot_change_makes_ready_writer_handoff_stale(self) -> None:
        prepared = self.prepare("writer")
        (self.run / SNAPSHOT_FILE).write_text("tampered", encoding="utf-8")
        shown = handoff.show(self.run)
        self.assertEqual(shown["effective_status"], "stale")
        self.assertIn(f"input hash changed: {SNAPSHOT_FILE}", shown["blocking_reasons"])
        self.assertEqual(prepared["manifest"]["to_role"], "writer")

    def test_writer_rejects_ready_status_that_does_not_match_snapshot(self) -> None:
        status = json.loads((self.run / "status.json").read_text(encoding="utf-8"))
        status["voice_id"] = "sharp-commentary"
        (self.run / "status.json").write_text(json.dumps(status), encoding="utf-8")
        with self.assertRaisesRegex(handoff.HandoffError, "does not match Voice Snapshot"):
            self.prepare("writer")

    def test_legacy_voice_does_not_change_existing_handoff_inputs(self) -> None:
        legacy = Path(self.temporary.name) / "legacy"
        legacy.mkdir()
        (legacy / "brief.md").write_text("brief", encoding="utf-8")
        (legacy / "status.json").write_text(json.dumps({
            "task_id": "TASK-LEGACY", "mode": "deep", "execution": "multi_agent", "status": "in_progress",
        }), encoding="utf-8")
        manifest = handoff.prepare(legacy, to_role="writer", phase="draft", objective="objective", decision_to_inform="decision", inputs=["brief.md"], write_scope=["output.md"], done_criteria=["done"])["manifest"]
        self.assertNotIn(SNAPSHOT_FILE, [item["path"] for item in manifest["allowed_inputs"]])

        extraneous = Path(self.temporary.name) / "legacy-extraneous"
        extraneous.mkdir()
        (extraneous / "brief.md").write_text("brief", encoding="utf-8")
        (extraneous / "status.json").write_text(json.dumps({
            "task_id": "TASK-LEGACY-EXTRA", "mode": "deep", "execution": "multi_agent", "status": "in_progress",
        }), encoding="utf-8")
        (extraneous / SNAPSHOT_FILE).write_text("extraneous", encoding="utf-8")
        with self.assertRaisesRegex(handoff.HandoffError, "requires voice_snapshot=ready"):
            handoff.prepare(extraneous, to_role="writer", phase="draft", objective="objective", decision_to_inform="decision", inputs=["brief.md", SNAPSHOT_FILE], write_scope=["output.md"], done_criteria=["done"])

        pending = Path(self.temporary.name) / "pending"
        pending.mkdir()
        (pending / "brief.md").write_text("brief", encoding="utf-8")
        (pending / "status.json").write_text(json.dumps({
            "task_id": "TASK-PENDING", "mode": "deep", "execution": "multi_agent",
            "voice_id": "clear-analytical", "voice_snapshot": "pending",
        }), encoding="utf-8")
        with self.assertRaisesRegex(handoff.HandoffError, "must be ready"):
            handoff.prepare(pending, to_role="writer", phase="draft", objective="objective", decision_to_inform="decision", inputs=["brief.md"], write_scope=["output.md"], done_criteria=["done"])


if __name__ == "__main__":
    unittest.main()
