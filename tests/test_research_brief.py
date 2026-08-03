from __future__ import annotations

import copy
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import writing_master.research_brief as research_brief_module
import writing_master.handoff as handoff
from writing_master.personal_context import (
    ContextError,
    ContextStore,
    atomic_write_json,
    canonical_sha256,
    normalized_content_sha256,
    read_json,
)
from writing_master.research_brief import (
    RESEARCH_BRIEF_FILE,
    make_evidence_id,
    save_research_brief,
    validate_research_brief_draft,
    verify_research_brief,
)


NOW = datetime(2026, 7, 28, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[1]


def _save_competing_research_brief(run_dir: str, draft: dict, barrier, results) -> None:
    try:
        barrier.wait(timeout=5)
        document = save_research_brief(run_dir, draft, now=NOW)
        results.put(("ok", document["candidates"][0]["topic"], document["research_brief_sha256"]))
    except ContextError as error:
        results.put(("error", error.code))


def _attempt_research_brief_save(run_dir: str, draft: dict, results) -> None:
    try:
        save_research_brief(run_dir, draft, now=NOW)
        results.put(("ok", None))
    except ContextError as error:
        results.put(("error", error.code))


def _save_after_lock_inode_recreation(
    run_dir: str, draft: dict, old_lock_holder: bool, recreated, barrier, results
) -> None:
    """Run two saves after unlink/recreate leaves them holding distinct lock inodes."""
    original_publish = research_brief_module._publish_json_once_at

    @contextmanager
    def partitioned_lock(run_fd):
        if old_lock_holder:
            descriptor = os.open(".research-brief.lock", os.O_RDWR, dir_fd=run_fd)
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            os.unlink(".research-brief.lock", dir_fd=run_fd)
            replacement = os.open(
                ".research-brief.lock",
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
                dir_fd=run_fd,
            )
            os.close(replacement)
            recreated.set()
        else:
            if not recreated.wait(timeout=5):
                raise RuntimeError("lock recreation did not complete")
            descriptor = os.open(".research-brief.lock", os.O_RDWR, dir_fd=run_fd)
            fcntl.flock(descriptor, fcntl.LOCK_EX)
        try:
            yield descriptor
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    def publish_together(run_fd, name, value):
        barrier.wait(timeout=5)
        return original_publish(run_fd, name, value)

    try:
        with (
            mock.patch.object(research_brief_module, "_research_brief_lock", partitioned_lock),
            mock.patch.object(research_brief_module, "_assert_lock_integrity", return_value=None),
            mock.patch.object(research_brief_module, "_publish_json_once_at", side_effect=publish_together),
        ):
            document = save_research_brief(run_dir, draft, now=NOW)
        results.put(("ok", document["candidates"][0]["topic"]))
    except ContextError as error:
        results.put(("error", error.code))


class ResearchBriefTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name) / "home"
        self.store = ContextStore(self.home)
        self.store.initialize()
        self.run = self.create_run("TASK-C-001")

    def create_run(self, task_id: str, *, materials: list[tuple[str, str]] | None = None) -> Path:
        run = Path(self.temporary.name) / "runs" / task_id
        run.mkdir(parents=True)
        (run / "status.json").write_text(json.dumps({"task_id": task_id}), encoding="utf-8")
        (run / "brief.md").write_bytes(b"# Synthetic topic discovery\r\n")
        self.store.create_snapshot(run, materials=[] if materials is None else materials)
        return run

    def snapshot(self, run: Path | None = None) -> dict:
        return read_json((self.run if run is None else run) / "personal-context-snapshot.json")

    def validate_draft(self, draft: dict, *, run: Path | None = None) -> None:
        validate_research_brief_draft(draft, self.snapshot(run), now=NOW)

    def fixture_draft(self) -> dict:
        return json.loads(
            (ROOT / "tests/fixtures/research-brief/draft-v1.json").read_text(encoding="utf-8")
        )

    def evidence(self, suffix: str = "one") -> dict:
        text = f"Synthetic evidence {suffix}."
        value = {
            "source_url": f"https://example.test/{suffix}",
            "source_date": "2026-07-27",
            "content_sha256": normalized_content_sha256(text),
        }
        return {
            "evidence_id": make_evidence_id(value),
            "source_title": f"Synthetic Source {suffix}",
            "publisher": "Synthetic Research",
            "observed_at": "2026-07-27T11:30:00+00:00",
            "evidence_text": text,
            **value,
        }

    def candidate(self, index: int) -> dict:
        evidence = self.evidence(str(index))
        return {
            "candidate_id": f"topic-{index:03d}",
            "topic": f"Synthetic Topic {index}",
            "heat": {
                "score": 8.5,
                "basis": "Synthetic sources are recent.",
                "as_of": "2026-07-27T12:00:00+00:00",
                "evidence_ids": [evidence["evidence_id"]],
            },
            "audience": "Software developers",
            "angle": "Use verifiable execution as the decision lens.",
            "evidence": [evidence],
            "scores": {
                "heat": {"value": 8.5, "rationale": "Recent sources."},
                "user_value": {"value": 8.0, "rationale": "Supports a decision."},
                "differentiation": {"value": 7.5, "rationale": "Not a feature list."},
                "author_fit": {
                    "value": 6.0,
                    "rationale": "Empty profile is explicitly treated as limited context.",
                    "references": [{
                        "kind": "profile",
                        "profile_id": "author-default",
                        "revision": 0,
                        "content_sha256": "eb7877b5514de357ac7596eb7f894c85985b67f0e1ff39158d1f2cb121351452",
                    }],
                },
            },
            "rationale": "A useful synthetic candidate.",
        }

    def draft(self) -> dict:
        return {"schema_version": 1, "candidates": [self.candidate(i) for i in range(1, 4)]}

    def assert_error(self, code: str, callback) -> None:
        with self.assertRaises(ContextError) as captured:
            callback()
        self.assertEqual(code, captured.exception.code)

    def test_save_and_verify_canonical_brief(self):
        document = save_research_brief(self.run, self.draft(), now=NOW)

        self.assertEqual(document["task_id"], "TASK-C-001")
        self.assertEqual(document["created_at"], "2026-07-28T00:00:00+00:00")
        self.assertEqual(document["inputs"]["brief"]["sha256"], hashlib.sha256((self.run / "brief.md").read_bytes()).hexdigest())
        self.assertEqual(document["inputs"]["personal_context"]["snapshot_sha256"], self.snapshot()["snapshot_sha256"])
        self.assertEqual([item["candidate_id"] for item in document["candidates"]], ["topic-001", "topic-002", "topic-003"])
        self.assertTrue((self.run / RESEARCH_BRIEF_FILE).is_file())
        verified = verify_research_brief(self.run, now=NOW)
        self.assertEqual((verified["verified"], verified["candidate_count"]), (True, 3))
        self.assertEqual(
            document["research_brief_sha256"],
            canonical_sha256({key: value for key, value in document.items() if key != "research_brief_sha256"}),
        )

    def test_checked_in_fixture_is_a_valid_empty_profile_draft(self):
        self.validate_draft(self.fixture_draft())

    def test_topic_research_handoff_contract_accepts_draft_that_runtime_can_save(self):
        draft_path = ROOT / "tests/fixtures/research-brief/draft-v1.json"
        atomic_write_json(self.run / "status.json", {
            "task_id": "TASK-C-001",
            "mode": "deep",
            "execution": "multi_agent",
            "status": "in_progress",
        })
        prepared = handoff.prepare(
            self.run,
            to_role="researcher",
            phase="topic_research",
            objective="Generate ranked topic candidates from current evidence.",
            decision_to_inform="Lead and user candidate selection.",
            inputs=["brief.md", "personal-context-snapshot.json"],
            write_scope=["research-brief-draft.json"],
            expected_outputs=["research-brief-draft.json"],
            done_criteria=["3-10 validated candidates with current evidence."],
            forbidden_inputs=["personal-context/author-profile.json"],
        )
        manifest = prepared["manifest"]
        attempt_dir = prepared["attempt_dir"]
        expected_inputs = [
            {
                "path": "brief.md",
                "sha256": hashlib.sha256((self.run / "brief.md").read_bytes()).hexdigest(),
                "required": True,
            },
            {
                "path": "personal-context-snapshot.json",
                "sha256": hashlib.sha256(
                    (self.run / "personal-context-snapshot.json").read_bytes()
                ).hexdigest(),
                "required": True,
            },
        ]
        self.assertEqual(manifest["allowed_inputs"], expected_inputs)
        self.assertEqual(manifest["role_card"], "skills/writing-master/agents/researcher.md")
        self.assertTrue((ROOT / manifest["role_card"]).is_file())
        self.assertEqual(manifest["write_scope"], ["research-brief-draft.json"])
        self.assertEqual(manifest["expected_outputs"], ["research-brief-draft.json"])
        self.assertEqual(
            manifest["output_root"],
            f"{attempt_dir.relative_to(self.run).as_posix()}/outputs",
        )
        self.assertEqual(
            manifest["result_path"],
            f"{attempt_dir.relative_to(self.run).as_posix()}/result.json",
        )

        agent_ref = "researcher-topic-fixture"
        self.assertEqual(handoff.mark_running(self.run, agent_ref)["status"], "running")
        staged_draft = self.run / manifest["output_root"] / "research-brief-draft.json"
        staged_draft.write_bytes(draft_path.read_bytes())
        result = {
            "schema_version": 1,
            "handoff_id": manifest["handoff_id"],
            "attempt": 1,
            "agent_ref": agent_ref,
            "status": "completed",
            "outputs": [{
                "logical_name": "research-brief-draft.json",
                "path": "outputs/research-brief-draft.json",
                "sha256": hashlib.sha256(staged_draft.read_bytes()).hexdigest(),
            }],
            "blocking_issues": [],
            "summary": "Synthetic topic research draft completed.",
            "completed_at": "2026-07-27T12:00:00+00:00",
        }

        atomic_write_json(self.run / manifest["result_path"], result)
        completed = handoff.complete(self.run)
        self.assertEqual(completed["state"]["status"], "completed")
        promoted_draft = self.run / "research-brief-draft.json"
        self.assertEqual(promoted_draft.read_bytes(), draft_path.read_bytes())
        self.assertEqual(handoff.show(self.run)["effective_status"], "completed")

        document = save_research_brief(
            self.run,
            json.loads(promoted_draft.read_text(encoding="utf-8")),
            now=NOW,
        )
        self.assertEqual(len(document["candidates"]), 3)
        self.assertTrue(verify_research_brief(self.run, now=NOW)["verified"])

    def test_candidate_count_identity_and_exact_fields_are_enforced(self):
        cases = []
        too_few = self.draft()
        too_few["candidates"] = too_few["candidates"][:2]
        cases.append(too_few)
        too_many = self.draft()
        too_many["candidates"] = [self.candidate(index) for index in range(1, 12)]
        cases.append(too_many)
        duplicate = self.draft()
        duplicate["candidates"][1]["candidate_id"] = duplicate["candidates"][0]["candidate_id"]
        cases.append(duplicate)
        unsafe = self.draft()
        unsafe["candidates"][0]["candidate_id"] = "../topic"
        cases.append(unsafe)
        whitespace = self.draft()
        whitespace["candidates"][0]["candidate_id"] = "   "
        cases.append(whitespace)
        missing = self.draft()
        del missing["candidates"][0]["audience"]
        cases.append(missing)
        extra = self.draft()
        extra["candidates"][0]["unexpected"] = True
        cases.append(extra)
        for draft in cases:
            with self.subTest(draft=draft):
                self.assert_error("invalid_input", lambda draft=draft: self.validate_draft(draft))

    def test_candidate_id_rejects_controls_and_bidi_format_but_keeps_normal_unicode(self):
        for unsafe_id in ("topic\x01", "topic\u0085", "topic\u202e", "topic\u200f"):
            draft = self.draft()
            draft["candidates"][0]["candidate_id"] = unsafe_id
            with self.subTest(candidate_id=repr(unsafe_id)):
                self.assert_error("invalid_input", lambda draft=draft: self.validate_draft(draft))

        draft = self.draft()
        draft["candidates"][0]["candidate_id"] = "主题-001"
        self.validate_draft(draft)

    def test_scores_reject_bool_non_finite_huge_range_empty_rationale_and_heat_mismatch(self):
        mutations = [
            lambda draft: draft["candidates"][0]["scores"]["user_value"].__setitem__("value", True),
            lambda draft: draft["candidates"][0]["scores"]["user_value"].__setitem__("value", float("inf")),
            lambda draft: draft["candidates"][0]["scores"]["user_value"].__setitem__("value", float("nan")),
            lambda draft: draft["candidates"][0]["scores"]["user_value"].__setitem__("value", 10**10000),
            lambda draft: draft["candidates"][0]["scores"]["user_value"].__setitem__("value", -0.1),
            lambda draft: draft["candidates"][0]["scores"]["user_value"].__setitem__("value", 10.1),
            lambda draft: draft["candidates"][0]["scores"]["user_value"].__setitem__("rationale", ""),
            lambda draft: draft["candidates"][0]["scores"].pop("differentiation"),
            lambda draft: draft["candidates"][0]["scores"]["author_fit"].__setitem__("references", []),
            lambda draft: draft["candidates"][0]["heat"].__setitem__("score", 10**10000),
            lambda draft: draft["candidates"][0]["scores"]["heat"].__setitem__("value", 7.0),
        ]
        for mutate in mutations:
            draft = self.draft()
            mutate(draft)
            with self.subTest(mutation=mutate):
                self.assert_error("invalid_input", lambda draft=draft: self.validate_draft(draft))

    def test_time_contract_rejects_bad_rfc3339_future_and_evidence_order(self):
        mutations = [
            lambda draft: draft["candidates"][0]["heat"].__setitem__("as_of", "2026-07-27"),
            lambda draft: draft["candidates"][0]["heat"].__setitem__("as_of", "2026-07-29T00:00:00+00:00"),
            lambda draft: draft["candidates"][0]["evidence"][0].__setitem__("observed_at", "2026-07-27T12:00:01+00:00"),
            lambda draft: draft["candidates"][0]["evidence"][0].__setitem__("source_date", "2026-07-28"),
            lambda draft: draft["candidates"][0]["evidence"][0].__setitem__("source_date", "20260727"),
        ]
        for mutate in mutations:
            draft = self.draft()
            mutate(draft)
            with self.subTest(mutation=mutate):
                self.assert_error("invalid_input", lambda draft=draft: self.validate_draft(draft))

    def test_invalid_unicode_evidence_text_and_utc_overflow_are_input_errors(self):
        invalid_unicode = self.draft()
        invalid_unicode["candidates"][0]["evidence"][0]["evidence_text"] = "\ud800"
        self.assert_error("invalid_input", lambda: self.validate_draft(invalid_unicode))

        invalid_candidate_text = self.draft()
        invalid_candidate_text["candidates"][0]["topic"] = "\ud800"
        self.assert_error("invalid_input", lambda: self.validate_draft(invalid_candidate_text))

        utc_overflow = self.draft()
        utc_overflow["candidates"][0]["heat"]["as_of"] = "0001-01-01T00:00:00+23:59"
        self.assert_error("invalid_input", lambda: self.validate_draft(utc_overflow))

    def test_evidence_url_hash_stable_id_uniqueness_and_heat_references(self):
        bad_hash = self.draft()
        bad_hash["candidates"][0]["evidence"][0]["content_sha256"] = "0" * 64
        self.assert_error("hash_mismatch", lambda: self.validate_draft(bad_hash))

        bad_id = self.draft()
        bad_id["candidates"][0]["evidence"][0]["evidence_id"] = "evidence-deadbeefdeadbeef"
        self.assert_error("hash_mismatch", lambda: self.validate_draft(bad_id))

        for bad_url in ("relative/path", "ftp://example.test/item", "http://[::1", "http://example.test:bad"):
            draft = self.draft()
            evidence = draft["candidates"][0]["evidence"][0]
            evidence["source_url"] = bad_url
            evidence["evidence_id"] = make_evidence_id(evidence)
            draft["candidates"][0]["heat"]["evidence_ids"] = [evidence["evidence_id"]]
            with self.subTest(url=bad_url):
                self.assert_error("invalid_input", lambda draft=draft: self.validate_draft(draft))

        missing_reference = self.draft()
        missing_reference["candidates"][0]["heat"]["evidence_ids"] = ["evidence-0000000000000000"]
        self.assert_error("unknown_id", lambda: self.validate_draft(missing_reference))

        duplicate = self.draft()
        evidence = copy.deepcopy(duplicate["candidates"][0]["evidence"][0])
        duplicate["candidates"][0]["evidence"].append(evidence)
        self.assert_error("invalid_input", lambda: self.validate_draft(duplicate))

        duplicate_heat_reference = self.draft()
        evidence_id = duplicate_heat_reference["candidates"][0]["heat"]["evidence_ids"][0]
        duplicate_heat_reference["candidates"][0]["heat"]["evidence_ids"] = [evidence_id, evidence_id]
        self.assert_error("invalid_input", lambda: self.validate_draft(duplicate_heat_reference))

    def test_profile_reference_must_match_snapshot(self):
        bad = self.draft()
        bad["candidates"][0]["scores"]["author_fit"]["references"][0]["revision"] = 1
        self.assert_error("hash_mismatch", lambda: self.validate_draft(bad))

    def test_material_author_fit_must_reference_a_selected_snapshot_item(self):
        source = Path(self.temporary.name) / "material.md"
        source.write_text("Synthetic selected material", encoding="utf-8")
        material = self.store.add_material(
            source,
            kind="experiences",
            title="Selected material",
            source_kind="user_provided",
            source_ref="local://selected-material",
            visibility="publishable",
        )
        run = self.create_run("TASK-C-MATERIAL", materials=[(material["item_id"], "background")])
        draft = self.draft()
        draft["candidates"][0]["scores"]["author_fit"]["references"] = [
            {"kind": "material", "item_id": material["item_id"]}
        ]
        self.validate_draft(draft, run=run)

        draft["candidates"][0]["scores"]["author_fit"]["references"][0]["item_id"] = "knowledge-0000000000000000"
        self.assert_error("unknown_id", lambda: self.validate_draft(draft, run=run))

        snapshot = self.snapshot(run)
        selected = snapshot["materials"][0]
        selected["item_id"] = "素材 1"
        selected["metadata"]["item_id"] = "素材 1"
        selected["copy_path"] = "context-materials/素材 1.md"
        selected["metadata_sha256"] = canonical_sha256(selected["metadata"])
        snapshot["snapshot_sha256"] = canonical_sha256(
            {key: value for key, value in snapshot.items() if key != "snapshot_sha256"}
        )
        draft["candidates"][0]["scores"]["author_fit"]["references"][0]["item_id"] = "素材 1"
        validate_research_brief_draft(draft, snapshot, now=NOW)

    def test_same_save_is_idempotent_and_different_save_is_duplicate(self):
        first = save_research_brief(self.run, self.draft(), now=NOW)
        self.assertEqual(first, save_research_brief(self.run, self.draft(), now=NOW))
        changed = self.draft()
        changed["candidates"][0]["topic"] = "A different topic"
        self.assert_error("duplicate", lambda: save_research_brief(self.run, changed, now=NOW))

    def test_existing_identical_brief_is_idempotent_after_clock_rolls_back(self):
        first = save_research_brief(self.run, self.draft(), now=NOW)
        second = save_research_brief(self.run, self.draft(), now=NOW - timedelta(days=1))
        self.assertEqual(second, first)

    def test_malformed_existing_canonical_uses_schema_error_on_save(self):
        save_research_brief(self.run, self.draft(), now=NOW)
        atomic_write_json(self.run / RESEARCH_BRIEF_FILE, {})
        self.assert_error(
            "schema_unsupported",
            lambda: save_research_brief(self.run, self.draft(), now=NOW),
        )

        run = self.create_run("TASK-C-BAD-CREATED-AT")
        document = save_research_brief(run, self.draft(), now=NOW)
        document["created_at"] = "not-a-time"
        document["research_brief_sha256"] = canonical_sha256(
            {key: value for key, value in document.items() if key != "research_brief_sha256"}
        )
        atomic_write_json(run / RESEARCH_BRIEF_FILE, document)
        self.assert_error(
            "schema_unsupported",
            lambda: save_research_brief(run, self.draft(), now=NOW),
        )

    def test_changed_brief_breaks_verify(self):
        save_research_brief(self.run, self.draft(), now=NOW)
        (self.run / "brief.md").write_text("Changed brief\n", encoding="utf-8")
        self.assert_error("hash_mismatch", lambda: verify_research_brief(self.run, now=NOW))

    def test_changed_snapshot_and_canonical_tampering_break_verify(self):
        save_research_brief(self.run, self.draft(), now=NOW)
        snapshot = self.snapshot()
        snapshot["created_at"] = "2026-07-27T00:00:00+00:00"
        snapshot["snapshot_sha256"] = canonical_sha256(
            {key: value for key, value in snapshot.items() if key != "snapshot_sha256"}
        )
        atomic_write_json(self.run / "personal-context-snapshot.json", snapshot)
        self.assert_error("hash_mismatch", lambda: verify_research_brief(self.run, now=NOW))

        run = self.create_run("TASK-C-TAMPER")
        document = save_research_brief(run, self.draft(), now=NOW)
        document["candidates"][0]["topic"] = "Tampered without updating self hash"
        atomic_write_json(run / RESEARCH_BRIEF_FILE, document)
        self.assert_error("hash_mismatch", lambda: verify_research_brief(run, now=NOW))

        run = self.create_run("TASK-C-SCHEMA")
        document = save_research_brief(run, self.draft(), now=NOW)
        document["schema_version"] = 2
        document["research_brief_sha256"] = canonical_sha256(
            {key: value for key, value in document.items() if key != "research_brief_sha256"}
        )
        atomic_write_json(run / RESEARCH_BRIEF_FILE, document)
        self.assert_error("schema_unsupported", lambda: verify_research_brief(run, now=NOW))

        run = self.create_run("TASK-C-TASK-ID")
        document = save_research_brief(run, self.draft(), now=NOW)
        document["task_id"] = "TASK-C-OTHER"
        document["research_brief_sha256"] = canonical_sha256(
            {key: value for key, value in document.items() if key != "research_brief_sha256"}
        )
        atomic_write_json(run / RESEARCH_BRIEF_FILE, document)
        self.assert_error("hash_mismatch", lambda: verify_research_brief(run, now=NOW))

    def test_status_task_id_is_required_input(self):
        for value in (None, ""):
            run = self.create_run(f"TASK-C-STATUS-{str(value)}")
            status = {} if value is None else {"task_id": value}
            atomic_write_json(run / "status.json", status)
            with self.subTest(value=value):
                self.assert_error("invalid_input", lambda run=run: save_research_brief(run, self.draft(), now=NOW))

    def test_competing_saves_have_one_canonical_winner(self):
        barrier = multiprocessing.Barrier(2)
        results = multiprocessing.Queue()
        first = self.draft()
        second = self.draft()
        second["candidates"][0]["topic"] = "Competing topic"
        processes = [
            multiprocessing.Process(
                target=_save_competing_research_brief,
                args=(str(self.run), draft, barrier, results),
            )
            for draft in (first, second)
        ]
        for process in processes:
            process.start()
        for process in processes:
            process.join(5)
            self.assertEqual(process.exitcode, 0)
        outcomes = [results.get(timeout=2) for _ in processes]
        self.assertCountEqual([outcome[0] for outcome in outcomes], ["ok", "error"])
        self.assertEqual([outcome[1] for outcome in outcomes if outcome[0] == "error"], ["duplicate"])
        successful_topic = next(outcome[1] for outcome in outcomes if outcome[0] == "ok")
        stored = read_json(self.run / RESEARCH_BRIEF_FILE)
        self.assertEqual(stored["candidates"][0]["topic"], successful_topic)
        self.assertTrue(verify_research_brief(self.run, now=NOW)["verified"])

    def test_no_clobber_publish_keeps_one_winner_after_lock_inode_recreation(self):
        (self.run / ".research-brief.lock").write_text("", encoding="utf-8")
        barrier = multiprocessing.Barrier(2)
        recreated = multiprocessing.Event()
        results = multiprocessing.Queue()
        first = self.draft()
        second = self.draft()
        second["candidates"][0]["topic"] = "Different lock-inode contender"
        processes = [
            multiprocessing.Process(
                target=_save_after_lock_inode_recreation,
                args=(str(self.run), draft, old_lock_holder, recreated, barrier, results),
            )
            for draft, old_lock_holder in ((first, True), (second, False))
        ]
        for process in processes:
            process.start()
        for process in processes:
            process.join(5)
            self.assertEqual(process.exitcode, 0)
        outcomes = [results.get(timeout=2) for _ in processes]
        self.assertCountEqual([outcome[0] for outcome in outcomes], ["ok", "error"])
        self.assertEqual([outcome[1] for outcome in outcomes if outcome[0] == "error"], ["duplicate"])
        winner = next(outcome[1] for outcome in outcomes if outcome[0] == "ok")
        self.assertEqual(read_json(self.run / RESEARCH_BRIEF_FILE)["candidates"][0]["topic"], winner)
        self.assertEqual(list(self.run.glob(f".{RESEARCH_BRIEF_FILE}.*")), [])

    def test_atomic_publish_failure_leaves_no_partial_brief(self):
        with mock.patch.object(research_brief_module.os, "link", side_effect=OSError("blocked")):
            with self.assertRaises(OSError):
                save_research_brief(self.run, self.draft(), now=NOW)

        self.assertFalse((self.run / RESEARCH_BRIEF_FILE).exists())
        self.assertEqual(list(self.run.glob(f".{RESEARCH_BRIEF_FILE}.*")), [])

    def test_lock_replacement_before_write_is_detected(self):
        original = research_brief_module._assert_lock_integrity
        calls = 0

        def replace_lock_then_assert(run_fd, lock_fd):
            nonlocal calls
            calls += 1
            if calls == 2:
                os.unlink(".research-brief.lock", dir_fd=run_fd)
                descriptor = os.open(
                    ".research-brief.lock",
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600,
                    dir_fd=run_fd,
                )
                os.close(descriptor)
            return original(run_fd, lock_fd)

        with mock.patch.object(research_brief_module, "_assert_lock_integrity", side_effect=replace_lock_then_assert):
            self.assert_error("path_escape", lambda: save_research_brief(self.run, self.draft(), now=NOW))
        self.assertFalse((self.run / RESEARCH_BRIEF_FILE).exists())

    def test_save_keeps_the_original_run_directory_when_an_ancestor_is_retargeted(self):
        base = Path(self.temporary.name) / "retarget-base"
        run = base / "runs" / "TASK-C-RETARGET"
        run.mkdir(parents=True)
        (run / "status.json").write_text('{"task_id":"TASK-C-RETARGET"}', encoding="utf-8")
        (run / "brief.md").write_text("# Anchored run\n", encoding="utf-8")
        self.store.create_snapshot(run, materials=[])

        moved = Path(self.temporary.name) / "retarget-original"
        outside = Path(self.temporary.name) / "retarget-outside"
        (outside / "runs" / "TASK-C-RETARGET").mkdir(parents=True)
        original_validate = research_brief_module.validate_research_brief
        swapped = False

        def validate_then_swap(document, snapshot, *, now=None):
            nonlocal swapped
            original_validate(document, snapshot, now=now)
            if not swapped:
                base.rename(moved)
                base.symlink_to(outside, target_is_directory=True)
                swapped = True

        with mock.patch.object(
            research_brief_module,
            "validate_research_brief",
            side_effect=validate_then_swap,
        ):
            save_research_brief(run, self.draft(), now=NOW)

        self.assertTrue((moved / "runs" / "TASK-C-RETARGET" / RESEARCH_BRIEF_FILE).is_file())
        self.assertFalse((outside / "runs" / "TASK-C-RETARGET" / RESEARCH_BRIEF_FILE).exists())

    def test_opening_the_run_has_no_resolve_then_open_retarget_window(self):
        base = Path(self.temporary.name) / "resolve-window-base"
        run = base / "runs" / "TASK-C-RESOLVE-WINDOW"
        run.mkdir(parents=True)
        (run / "status.json").write_text('{"task_id":"TASK-C-RESOLVE-WINDOW"}', encoding="utf-8")
        (run / "brief.md").write_text("# Resolve window\n", encoding="utf-8")
        self.store.create_snapshot(run, materials=[])

        moved = Path(self.temporary.name) / "resolve-window-original"
        outside = Path(self.temporary.name) / "resolve-window-outside"
        outside_run = outside / "runs" / "TASK-C-RESOLVE-WINDOW"
        outside_run.mkdir(parents=True)
        (outside_run / "status.json").write_text('{"task_id":"TASK-C-RESOLVE-WINDOW"}', encoding="utf-8")
        (outside_run / "brief.md").write_text("# Outside\n", encoding="utf-8")
        outside_snapshot = self.snapshot(run)
        atomic_write_json(outside_run / "personal-context-snapshot.json", outside_snapshot)

        original_resolve = Path.resolve
        swapped = False

        def resolve_then_swap(path, *args, **kwargs):
            nonlocal swapped
            resolved = original_resolve(path, *args, **kwargs)
            if path == run and not swapped:
                base.rename(moved)
                base.symlink_to(outside, target_is_directory=True)
                swapped = True
            return resolved

        with mock.patch.object(Path, "resolve", new=resolve_then_swap):
            save_research_brief(run, self.draft(), now=NOW)

        self.assertTrue((base / "runs" / "TASK-C-RESOLVE-WINDOW" / RESEARCH_BRIEF_FILE).is_file())
        self.assertFalse((outside_run / RESEARCH_BRIEF_FILE).exists())

    def test_missing_corrupt_and_symlinked_run_inputs_are_rejected(self):
        missing = Path(self.temporary.name) / "missing"
        self.assert_error("not_initialized", lambda: save_research_brief(missing, self.draft(), now=NOW))
        self.assert_error("path_escape", lambda: save_research_brief("bad\x00run", self.draft(), now=NOW))

        detour = self.run.parent / "detour"
        detour.mkdir()
        parent_component_path = detour / ".." / self.run.name
        self.assert_error(
            "path_escape",
            lambda: save_research_brief(parent_component_path, self.draft(), now=NOW),
        )
        self.assertFalse((self.run / RESEARCH_BRIEF_FILE).exists())

        target = self.create_run("TASK-C-SYMLINK-TARGET")
        link = Path(self.temporary.name) / "run-link"
        link.symlink_to(target, target_is_directory=True)
        self.assert_error("path_escape", lambda: save_research_brief(link, self.draft(), now=NOW))

        run = self.create_run("TASK-C-CORRUPT")
        (run / "personal-context-snapshot.json").write_text("{", encoding="utf-8")
        self.assert_error("invalid_json", lambda: save_research_brief(run, self.draft(), now=NOW))

        run = self.create_run("TASK-C-DEEP-JSON")
        deeply_nested = '{"task_id":' + ("[" * 2000) + "0" + ("]" * 2000) + "}"
        (run / "status.json").write_text(deeply_nested, encoding="utf-8")
        self.assert_error("invalid_json", lambda: save_research_brief(run, self.draft(), now=NOW))

        run = self.create_run("TASK-C-BRIEF-LINK")
        outside = Path(self.temporary.name) / "outside-brief.md"
        outside.write_text("outside", encoding="utf-8")
        (run / "brief.md").unlink()
        (run / "brief.md").symlink_to(outside)
        self.assert_error("path_escape", lambda: save_research_brief(run, self.draft(), now=NOW))

    def test_fifo_inputs_outputs_and_lock_fail_without_blocking(self):
        cases = []
        brief_run = self.create_run("TASK-C-FIFO-BRIEF")
        (brief_run / "brief.md").unlink()
        os.mkfifo(brief_run / "brief.md")
        cases.append(brief_run)

        output_run = self.create_run("TASK-C-FIFO-OUTPUT")
        os.mkfifo(output_run / RESEARCH_BRIEF_FILE)
        cases.append(output_run)

        lock_run = self.create_run("TASK-C-FIFO-LOCK")
        os.mkfifo(lock_run / ".research-brief.lock")
        cases.append(lock_run)

        for run in cases:
            with self.subTest(run=run.name):
                results = multiprocessing.Queue()
                process = multiprocessing.Process(
                    target=_attempt_research_brief_save,
                    args=(str(run), self.draft(), results),
                )
                process.start()
                process.join(2)
                if process.is_alive():
                    process.terminate()
                    process.join(2)
                    self.fail(f"save blocked on non-regular file in {run}")
                self.assertEqual(process.exitcode, 0)
                self.assertEqual(results.get(timeout=1), ("error", "path_escape"))

    def test_runtime_never_reads_global_profile_style_or_material_indexes(self):
        with (
            mock.patch.object(ContextStore, "read_profile", side_effect=AssertionError("global profile read")),
            mock.patch.object(ContextStore, "read_style", side_effect=AssertionError("global style read")),
            mock.patch.object(ContextStore, "list_materials", side_effect=AssertionError("global material read")),
            mock.patch.object(ContextStore, "search_materials", side_effect=AssertionError("global search")),
        ):
            document = save_research_brief(self.run, self.draft(), now=NOW)
        self.assertEqual(document["task_id"], "TASK-C-001")


if __name__ == "__main__":
    unittest.main()
