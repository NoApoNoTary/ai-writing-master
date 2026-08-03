from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from writing_master import handoff
import writing_master.persona as persona
from writing_master.persona import PersonaError, PersonaStore
from writing_master.voice_presets import SNAPSHOT_FILE, VoicePresetStore


class PersonaStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.run = self.root / "run"
        self.run.mkdir()
        (self.run / "status.json").write_text(json.dumps({"task_id": "TASK-PERSONA"}), encoding="utf-8")
        self.skill = self.root / "persona"
        self.skill.mkdir()
        self.source = b"---\r\nname: synthetic-author\r\nversion: '2.1'\r\n---\r\nRaw body.\r\n"
        (self.skill / "SKILL.md").write_bytes(self.source)
        self.brief = "## Adopted parts\nAnalytical framing.\n\n## Boundaries\nFacts still require evidence.\n"
        self.store = PersonaStore()

    def create(self, **changes) -> dict:
        options = {
            "mode": "author",
            "content_type": "analysis",
            "background_mode": "project",
        }
        options.update(changes)
        return self.store.create_snapshot(self.run, self.skill, self.brief, **options)

    def assert_error(self, code: str, action) -> None:
        with self.assertRaises(PersonaError) as captured:
            action()
        self.assertEqual(captured.exception.code, code)

    def test_snapshot_preserves_source_and_records_free_form_brief_provenance(self) -> None:
        result = self.create()

        self.assertEqual((self.run / "persona-skill.md").read_bytes(), self.source)
        saved_brief = (self.run / "persona-brief.md").read_text(encoding="utf-8")
        self.assertTrue(saved_brief.endswith(self.brief))
        for token in (
            '"mode":"author"',
            '"content_type":"analysis"',
            '"background_mode":"project"',
            '"source_version":"2.1"',
            '"source_path":',
            '"source_sha256":',
            '"brief_sha256":',
        ):
            self.assertIn(token, saved_brief)
        self.assertEqual(result["source_version"], "2.1")

        status = json.loads((self.run / "status.json").read_text(encoding="utf-8"))
        self.assertEqual(status["persona_mode"], "author")
        self.assertEqual(status["persona_snapshot"], "ready")
        self.assertEqual(status["persona_source_sha256"], hashlib.sha256(self.source).hexdigest())
        self.assertEqual(
            status["persona_brief_sha256"],
            hashlib.sha256((self.run / "persona-brief.md").read_bytes()).hexdigest(),
        )
        self.assertTrue(self.store.verify_run(self.run)["verified"])
        self.assertEqual(self.store.read_task_brief(self.run), saved_brief)

    def test_same_request_is_idempotent_without_reopening_changed_external_source(self) -> None:
        first = self.create()
        saved_source = (self.run / "persona-skill.md").read_bytes()
        (self.skill / "SKILL.md").write_text("changed upstream", encoding="utf-8")

        self.assertEqual(self.create(), first)
        self.assertEqual((self.run / "persona-skill.md").read_bytes(), saved_source)
        self.assertTrue(self.store.verify_run(self.run)["verified"])

    def test_same_request_recovers_after_status_write_failure(self) -> None:
        with mock.patch.object(persona, "atomic_write_json_at", side_effect=OSError("blocked")):
            self.assert_error("path_escape", self.create)

        self.assertTrue((self.run / "persona-skill.md").is_file())
        self.assertTrue((self.run / "persona-brief.md").is_file())
        self.assertTrue(self.create()["verified"])

    def test_different_frozen_inputs_conflict(self) -> None:
        self.create()
        cases = (
            {"mode": "reference"},
            {"content_type": "review"},
            {"background_mode": "none"},
            {"source_version": "9"},
        )
        for changes in cases:
            with self.subTest(changes=changes):
                self.assert_error("snapshot_conflict", lambda changes=changes: self.create(**changes))
        self.assert_error(
            "snapshot_conflict",
            lambda: self.store.create_snapshot(
                self.run,
                self.skill,
                self.brief + "changed",
                mode="author",
                content_type="analysis",
                background_mode="project",
            ),
        )

    def test_missing_frontmatter_version_uses_content_hash_version(self) -> None:
        source = self.root / "plain.md"
        source.write_text("plain persona", encoding="utf-8")
        result = self.store.create_snapshot(
            self.run,
            source,
            self.brief,
            mode="reference",
            content_type="tutorial",
            background_mode="none",
        )
        self.assertEqual(result["source_version"], hashlib.sha256(source.read_bytes()).hexdigest())

    def test_explicit_version_is_used_only_when_frontmatter_has_none(self) -> None:
        source = self.root / "plain-versioned.md"
        source.write_text("plain persona", encoding="utf-8")
        result = self.store.create_snapshot(
            self.run,
            source,
            self.brief,
            mode="reference",
            content_type="tutorial",
            background_mode="none",
            source_version="nuwa-7",
        )
        self.assertEqual(result["source_version"], "nuwa-7")
        self.assertEqual(result["source_sha256"], hashlib.sha256(source.read_bytes()).hexdigest())

    def test_pending_content_contract_mode_is_frozen(self) -> None:
        (self.run / "status.json").write_text(json.dumps({
            "task_id": "TASK-PERSONA",
            "persona_mode": "author",
            "persona_snapshot": "pending",
            "persona_source_path": None,
            "persona_source_version": None,
            "persona_source_sha256": None,
            "persona_brief_sha256": None,
        }), encoding="utf-8")
        self.assert_error(
            "snapshot_conflict",
            lambda: self.create(mode="reference"),
        )
        self.assertEqual(self.create()["persona_mode"], "author")

    def test_pending_source_and_partial_status_cannot_be_silently_replaced(self) -> None:
        other = self.root / "other.md"
        other.write_text("other persona", encoding="utf-8")
        resolved = str((self.skill / "SKILL.md").resolve())
        (self.run / "status.json").write_text(json.dumps({
            "task_id": "TASK-PERSONA",
            "persona_mode": "author",
            "persona_snapshot": "pending",
            "persona_source_path": resolved,
            "persona_source_version": None,
            "persona_source_sha256": None,
            "persona_brief_sha256": None,
        }), encoding="utf-8")
        self.assert_error(
            "snapshot_conflict",
            lambda: self.store.create_snapshot(
                self.run,
                other,
                self.brief,
                mode="author",
                content_type="analysis",
                background_mode="project",
            ),
        )

    def test_verify_rejects_persona_files_without_ready_status(self) -> None:
        (self.run / "persona-skill.md").write_text("partial", encoding="utf-8")
        self.assert_error("snapshot_conflict", lambda: self.store.verify_run(self.run))
        self.assert_error("snapshot_conflict", self.create)

    def test_frontmatter_version_is_closed_top_level_and_not_overridable(self) -> None:
        self.assert_error(
            "invalid_input",
            lambda: self.create(source_version="forged"),
        )

        source = self.root / "frontmatter.md"
        source.write_text(
            "---\nmetadata:\n  version: nested\nversion: 7 # release\n---\nPersona\n",
            encoding="utf-8",
        )
        result = self.store.create_snapshot(
            self.run,
            source,
            self.brief,
            mode="reference",
            content_type="review",
            background_mode="none",
        )
        self.assertEqual(result["source_version"], "7")

        unclosed_run = self.root / "unclosed-run"
        unclosed_run.mkdir()
        (unclosed_run / "status.json").write_text(json.dumps({"task_id": "TASK-UNCLOSED"}), encoding="utf-8")
        unclosed = self.root / "unclosed.md"
        unclosed.write_text("---\nversion: forged\nPersona\n", encoding="utf-8")
        result = self.store.create_snapshot(
            unclosed_run,
            unclosed,
            self.brief,
            mode="reference",
            content_type="review",
            background_mode="none",
        )
        self.assertEqual(result["source_version"], hashlib.sha256(unclosed.read_bytes()).hexdigest())

    def test_verify_does_not_require_external_source_to_still_exist(self) -> None:
        self.create()
        (self.skill / "SKILL.md").unlink()
        self.skill.rmdir()
        self.assertTrue(self.store.verify_run(self.run)["verified"])

    def test_verify_detects_task_file_and_status_tampering(self) -> None:
        self.create()
        (self.run / "persona-skill.md").write_text("tampered", encoding="utf-8")
        self.assert_error("hash_mismatch", lambda: self.store.verify_run(self.run))

        run = self.root / "brief-tamper"
        run.mkdir()
        (run / "status.json").write_text(json.dumps({"task_id": "TASK-BRIEF"}), encoding="utf-8")
        self.store.create_snapshot(
            run,
            self.skill,
            self.brief,
            mode="author",
            content_type="story",
            background_mode="default",
        )
        with (run / "persona-brief.md").open("ab") as handle:
            handle.write(b"tampered")
        self.assert_error("hash_mismatch", lambda: self.store.verify_run(run))

    def test_none_and_explicit_source_resolution_do_not_scan(self) -> None:
        self.assertEqual(self.store.verify_run(self.run)["persona_mode"], "none")
        self.assertIsNone(self.store.read_task_brief(self.run))

        self.assert_error(
            "path_escape",
            lambda: self.store.create_snapshot(
                self.run,
                "bad\npath",
                self.brief,
                mode="author",
                content_type="opinion",
                background_mode="default",
            ),
        )

        no_skill = self.root / "no-skill"
        no_skill.mkdir()
        (no_skill / "other.md").write_text("persona", encoding="utf-8")
        self.assert_error(
            "not_initialized",
            lambda: self.store.create_snapshot(
                self.run,
                no_skill,
                self.brief,
                mode="author",
                content_type="opinion",
                background_mode="default",
            ),
        )

    def test_builtin_khazix_template_resolves_by_id_and_freezes_verbatim(self) -> None:
        result = self.store.create_snapshot(
            self.run,
            "khazix-writer",
            self.brief,
            mode="reference",
            content_type="analysis",
            background_mode="none",
        )

        self.assertEqual(result["source_input"], "khazix-writer")
        self.assertTrue(result["source_path"].endswith("persona_templates/khazix-writer/SKILL.md"))
        self.assertEqual(
            (self.run / "persona-skill.md").read_bytes(),
            Path(result["source_path"]).read_bytes(),
        )
        content = (self.run / "persona-skill.md").read_text(encoding="utf-8")
        self.assertIn("卡兹克科技观察", content)
        for rule_id in (
            *(f"R{number:02d}" for number in range(1, 26)),
            *(f"A{number:02d}" for number in range(1, 10)),
        ):
            self.assertIn(rule_id, content)


class PersonaHandoffTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.skill = self.root / "SKILL.md"
        self.skill.write_text("---\nname: persona\nversion: 1\n---\nPersona\n", encoding="utf-8")
        self.brief = "## Adopted parts\nJudgment habits.\n"

    def make_run(self, task_id: str) -> Path:
        run = self.root / task_id
        run.mkdir()
        (run / "status.json").write_text(json.dumps({
            "task_id": task_id,
            "mode": "deep",
            "execution": "multi_agent",
            "status": "in_progress",
        }), encoding="utf-8")
        (run / "brief.md").write_text("brief", encoding="utf-8")
        PersonaStore().create_snapshot(
            run,
            self.skill,
            self.brief,
            mode="reference",
            content_type="analysis",
            background_mode="none",
        )
        return run

    @staticmethod
    def prepare(run: Path, role: str, inputs: list[str] | None = None) -> dict:
        phase = {
            "researcher": "research",
            "editorial_strategist": "strategy",
            "writer": "draft",
            "auditor": "review",
        }[role]
        return handoff.prepare(
            run,
            to_role=role,
            phase=phase,
            objective="objective",
            decision_to_inform="decision",
            inputs=inputs or ["brief.md"],
            write_scope=["output.md"],
            done_criteria=["done"],
        )

    def test_same_brief_is_forced_for_editorial_writer_and_auditor(self) -> None:
        for role in ("editorial_strategist", "writer", "auditor"):
            with self.subTest(role=role):
                manifest = self.prepare(self.make_run(f"TASK-{role}"), role)["manifest"]
                paths = [item["path"] for item in manifest["allowed_inputs"]]
                self.assertIn("persona-brief.md", paths)
                self.assertNotIn("persona-skill.md", paths)

    def test_researcher_cannot_receive_persona_inputs(self) -> None:
        with self.assertRaisesRegex(handoff.HandoffError, "must not receive Persona inputs"):
            self.prepare(
                self.make_run("TASK-BRIEF-INPUT"),
                "researcher",
                ["brief.md", "persona-brief.md"],
            )
        with self.assertRaisesRegex(handoff.HandoffError, "raw Persona Skill"):
            self.prepare(
                self.make_run("TASK-SKILL-INPUT"),
                "researcher",
                ["brief.md", "persona-skill.md"],
            )

    def test_persona_brief_change_makes_handoff_stale(self) -> None:
        run = self.make_run("TASK-STALE")
        self.prepare(run, "writer")
        with (run / "persona-brief.md").open("ab") as handle:
            handle.write(b"tampered")
        shown = handoff.show(run)
        self.assertEqual(shown["effective_status"], "stale")
        self.assertIn("input hash changed: persona-brief.md", shown["blocking_reasons"])

    def test_selected_persona_without_ready_snapshot_blocks_persona_roles(self) -> None:
        for role in ("editorial_strategist", "writer", "auditor"):
            with self.subTest(role=role):
                run = self.root / f"TASK-MISSING-{role}"
                run.mkdir()
                (run / "brief.md").write_text("brief", encoding="utf-8")
                (run / "status.json").write_text(json.dumps({
                    "task_id": f"TASK-MISSING-{role}",
                    "mode": "deep",
                    "execution": "multi_agent",
                    "persona_mode": "author",
                    "persona_snapshot": "none",
                }), encoding="utf-8")
                with self.assertRaisesRegex(handoff.HandoffError, "must be ready"):
                    self.prepare(run, role)

    def test_skill_and_status_tampering_after_prepare_make_handoff_stale(self) -> None:
        skill_run = self.make_run("TASK-SKILL-STALE")
        self.prepare(skill_run, "writer")
        (skill_run / "persona-skill.md").write_text("tampered", encoding="utf-8")
        shown = handoff.show(skill_run)
        self.assertEqual(shown["effective_status"], "stale")
        self.assertTrue(any("task Persona Skill has changed" in reason for reason in shown["blocking_reasons"]))

        status_run = self.make_run("TASK-STATUS-STALE")
        self.prepare(status_run, "editorial_strategist")
        status = json.loads((status_run / "status.json").read_text(encoding="utf-8"))
        status.update({"persona_mode": "none", "persona_snapshot": "none"})
        (status_run / "status.json").write_text(json.dumps(status), encoding="utf-8")
        state = handoff.mark_running(status_run, "persona-status-tamper")
        self.assertEqual(state["status"], "stale")
        self.assertIn("Persona selection changed", state["reason"])

    def test_persona_and_voice_snapshots_are_both_preserved_for_writer(self) -> None:
        run = self.root / "TASK-COMBINED"
        run.mkdir()
        (run / "brief.md").write_text("brief", encoding="utf-8")
        (run / "status.json").write_text(json.dumps({
            "task_id": "TASK-COMBINED",
            "mode": "deep",
            "execution": "multi_agent",
            "status": "in_progress",
            "voice_snapshot": "pending",
        }), encoding="utf-8")
        PersonaStore().create_snapshot(
            run,
            self.skill,
            self.brief,
            mode="author",
            content_type="opinion",
            background_mode="default",
        )
        VoicePresetStore().create_snapshot(run, "clear-analytical")

        paths = [
            item["path"]
            for item in self.prepare(run, "writer")["manifest"]["allowed_inputs"]
        ]
        self.assertIn("persona-brief.md", paths)
        self.assertIn(SNAPSHOT_FILE, paths)


if __name__ == "__main__":
    unittest.main()
