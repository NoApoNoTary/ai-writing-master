from __future__ import annotations

import json
import hashlib
import multiprocessing
from pathlib import Path
import tempfile
import time
import threading
import unittest
from unittest import mock

import writing_master.personal_context as personal_context
from writing_master.personal_context import (
    ContextError,
    ContextStore,
    atomic_write_json,
    safe_path,
)


def _hold_context_lock(home: str, entered, release) -> None:
    with ContextStore(home).locked():
        entered.set()
        release.wait(5)


def _take_context_lock(home: str, acquired) -> None:
    with ContextStore(home).locked():
        acquired.set()


def _record_competing_context_usage(home: str, run_dir: str, uses: list[dict], write_barrier, results) -> None:
    original_write = personal_context.atomic_write_json_at

    def synchronized_write(directory_fd, name, value):
        if name == personal_context.USAGE_FILE:
            try:
                write_barrier.wait(timeout=0.5)
            except threading.BrokenBarrierError:
                pass
        return original_write(directory_fd, name, value)

    try:
        with mock.patch.object(personal_context, "atomic_write_json_at", side_effect=synchronized_write):
            usage = ContextStore(home).record_usage(
                run_dir,
                uses=uses,
                artifact_paths={"final": "final.md", "acceptance": "acceptance-report.md"},
            )
        results.put(("ok", usage["uses"]))
    except ContextError as error:
        results.put(("error", error.code))


def _approve_competing_material(home: str, run_dir: str, item_id: str, write_barrier, results) -> None:
    original_write = personal_context.atomic_write_json_at

    def synchronized_write(directory_fd, name, value):
        if name == personal_context.APPROVAL_FILE:
            try:
                write_barrier.wait(timeout=0.5)
            except threading.BrokenBarrierError:
                pass
        return original_write(directory_fd, name, value)

    try:
        with mock.patch.object(personal_context, "atomic_write_json_at", side_effect=synchronized_write):
            approval = ContextStore(home).approve(run_dir, item_id, allowed_use="background")
        results.put(("ok", approval))
    except ContextError as error:
        results.put(("error", error.code))


def _create_competing_snapshot(home: str, run_dir: str, item_id: str, build_barrier, results) -> None:
    original_now = personal_context._now

    def synchronized_now():
        try:
            build_barrier.wait(timeout=0.5)
        except threading.BrokenBarrierError:
            pass
        return original_now()

    try:
        with mock.patch.object(personal_context, "_now", side_effect=synchronized_now):
            snapshot = ContextStore(home).create_snapshot(
                run_dir,
                materials=[(item_id, "background")],
            )
        results.put(("ok", snapshot))
    except ContextError as error:
        results.put(("error", error.code))


def _wait_for_flock_waiter(lock_path: Path, process_id: int, timeout: float = 3) -> bool:
    """Wait until Linux reports this process blocked on this lock's inode."""
    deadline = time.monotonic() + timeout
    inode = lock_path.stat().st_ino
    while time.monotonic() < deadline:
        for line in Path("/proc/locks").read_text(encoding="utf-8").splitlines():
            fields = line.split()
            if fields[1:3] != ["->", "FLOCK"] or len(fields) < 7 or fields[5] != str(process_id):
                continue
            try:
                if int(fields[6].rsplit(":", 1)[1]) == inode:
                    return True
            except ValueError:
                continue
        time.sleep(0.01)
    return False


class PersonalContextStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name) / "home"
        self.store = ContextStore(self.home)

    def assert_error_code(self, code: str, call) -> None:
        with self.assertRaises(ContextError) as captured:
            call()
        self.assertEqual(code, captured.exception.code)

    def confirmed_profile(self, *, values=None) -> dict:
        return {
            "identity": {"display_name": "ROLE_A"},
            "expertise": ["AI Agent"],
            "content_directions": ["software development"],
            "values": ["evidence first"] if values is None else values,
            "expression": {"tone": ["analytical", "concise"]},
            "avoid": ["generic summaries"],
            "provenance": {"kind": "user_confirmed"},
        }

    def write_material(self, name: str, content: str | bytes) -> Path:
        path = Path(self.temporary.name) / name
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        return path

    def add_material(self, source: Path, **overrides) -> dict:
        values = {
            "kind": "experiences",
            "title": "Synthetic Orbit 17",
            "source_kind": "user_provided",
            "source_ref": "synthetic://orbit-17",
            "visibility": "ask_before_use",
            "tags": ["synthetic"],
            "summary": "",
        }
        values.update(overrides)
        return self.store.add_material(source, **values)

    def run_directory(self, task_id: str = "TASK-001") -> Path:
        run = Path(self.temporary.name) / "runs" / task_id
        run.mkdir(parents=True)
        (run / "status.json").write_text(json.dumps({"task_id": task_id, "mode": "standard"}), encoding="utf-8")
        return run

    def test_initialize_is_idempotent_and_creates_canonical_empty_documents(self):
        first = self.store.initialize()
        before = {path: path.read_bytes() for path in (
            self.store.profile_path,
            self.store.style_path,
            self.store.index_path,
        )}

        second = self.store.initialize()

        self.assertEqual(first, second)
        self.assertEqual(before, {path: path.read_bytes() for path in before})
        self.assertEqual(first["profile"]["revision"], 0)
        self.assertEqual(first["style"]["revision"], 0)
        self.assertEqual(first["index"], {"schema_version": 1, "revision": 0, "items": []})
        self.assertEqual(self.store.read_profile(), first["profile"])
        self.assertEqual(self.store.read_style(), first["style"])
        self.assertEqual(self.store.read_index(), first["index"])

    def test_read_before_initialize_is_rejected(self):
        self.assert_error_code("not_initialized", self.store.read_profile)

    def test_schema_and_revision_must_be_actual_integers(self):
        profile = self.store.initialize()["profile"]

        for field, invalid_value in (
            ("schema_version", True),
            ("schema_version", 1.0),
            ("revision", False),
            ("revision", 0.0),
        ):
            with self.subTest(field=field, invalid_value=invalid_value):
                malformed = dict(profile)
                malformed[field] = invalid_value
                atomic_write_json(self.store.profile_path, malformed)
                self.assert_error_code("schema_unsupported", self.store.read_profile)

    def test_atomic_replace_failure_preserves_prior_json(self):
        self.store.initialize()
        before = self.store.profile_path.read_bytes()

        with mock.patch("writing_master.personal_context.os.replace", side_effect=OSError("blocked")):
            with self.assertRaises(OSError):
                atomic_write_json(self.store.profile_path, {"replacement": True})

        self.assertEqual(self.store.profile_path.read_bytes(), before)
        self.assertEqual(list(self.store.root.glob(".author-profile.json.*")), [])

    def test_corrupt_json_is_rejected(self):
        self.store.initialize()
        self.store.profile_path.write_text("{", encoding="utf-8")

        self.assert_error_code("invalid_json", self.store.read_profile)

    def test_unsupported_schema_is_rejected(self):
        profile = self.store.initialize()["profile"]
        profile["schema_version"] = 2
        atomic_write_json(self.store.profile_path, profile)

        self.assert_error_code("schema_unsupported", self.store.read_profile)

    def test_profile_updates_are_revisioned_idempotent_and_conflict_safe(self):
        self.assertEqual(self.store.initialize()["profile"]["revision"], 0)
        first = self.store.update_profile(self.confirmed_profile(), expected_revision=0)
        self.assertEqual(first["revision"], 1)
        self.assertEqual(first["status"], "ready")
        self.assertEqual(
            self.store.update_profile(self.confirmed_profile(), expected_revision=1),
            first,
        )

        second = self.store.update_profile(
            self.confirmed_profile(values=["evidence first", "traceability"]),
            expected_revision=1,
        )
        self.assertEqual(second["revision"], 2)
        self.assert_error_code(
            "revision_conflict",
            lambda: self.store.update_profile(self.confirmed_profile(), expected_revision=1),
        )
        self.assertEqual(self.store.read_profile(), second)

    def test_stale_profile_revision_wins_over_malformed_payload(self):
        self.store.initialize()
        current = self.store.update_profile(self.confirmed_profile(), expected_revision=0)

        self.assert_error_code(
            "revision_conflict",
            lambda: self.store.update_profile({}, expected_revision=0),
        )
        self.assertEqual(self.store.read_profile(), current)

    def test_ready_profile_timestamps_are_rfc3339(self):
        self.store.initialize()
        ready = self.store.update_profile(self.confirmed_profile(), expected_revision=0)
        ready["updated_at"] = "2026-07-28T00:00:00Z"
        atomic_write_json(self.store.profile_path, ready)
        self.assertEqual(self.store.read_profile()["updated_at"], ready["updated_at"])

        for timestamp in ("2026-07-28 00:00:00+00:00", "2026-07-28T00:00:00+0000"):
            with self.subTest(timestamp=timestamp):
                malformed = dict(ready)
                malformed["updated_at"] = timestamp
                atomic_write_json(self.store.profile_path, malformed)
                self.assert_error_code("schema_unsupported", self.store.read_profile)

    def test_profile_update_keeps_directory_fd_after_root_path_swap(self):
        self.store.initialize()
        self.store.update_profile(self.confirmed_profile(), expected_revision=0)
        original_root = self.store.root
        parked_root = self.home / "parked-personal-context"
        outside = Path(self.temporary.name) / "outside"
        outside.mkdir()
        real_write = personal_context.atomic_write_json_at

        def swap_root_then_write(directory_fd, name, value):
            original_root.rename(parked_root)
            original_root.symlink_to(outside, target_is_directory=True)
            return real_write(directory_fd, name, value)

        with mock.patch.object(
            personal_context,
            "atomic_write_json_at",
            side_effect=swap_root_then_write,
        ):
            updated = self.store.update_profile(
                self.confirmed_profile(values=["evidence first", "traceability"]),
                expected_revision=1,
            )

        self.assertEqual(updated["revision"], 2)
        persisted = json.loads((parked_root / "author-profile.json").read_text(encoding="utf-8"))
        self.assertEqual(persisted["revision"], 2)
        self.assertFalse((outside / "author-profile.json").exists())

    def test_profile_update_rejects_home_symlink_retargeting(self):
        self.store.initialize()
        initial = self.store.update_profile(self.confirmed_profile(), expected_revision=0)
        parked_home = self.home.with_name("parked-home")
        outside = Path(self.temporary.name) / "outside"
        outside.mkdir()
        self.home.rename(parked_home)
        self.home.symlink_to(outside, target_is_directory=True)

        self.assert_error_code(
            "path_escape",
            lambda: self.store.update_profile(
                self.confirmed_profile(values=["evidence first", "traceability"]),
                expected_revision=1,
            ),
        )
        self.assertEqual(
            json.loads((parked_home / "personal-context" / "author-profile.json").read_text(encoding="utf-8")),
            initial,
        )
        self.assertFalse((outside / "personal-context" / "author-profile.json").exists())

    def test_material_add_copies_all_five_kinds_with_traceable_hashes(self):
        self.store.initialize()
        source = self.write_material("orbit-17.md", "Orbit 17\r\n合成素材\n")
        cases = (
            ("experiences", "user_provided"),
            ("opinions", "user_confirmed"),
            ("cases", "user_provided"),
            ("references", "external_reference"),
            ("previous_articles", "user_provided"),
        )
        items = [
            self.add_material(
                source,
                kind=kind,
                source_kind=source_kind,
                source_ref=f"synthetic://{kind}",
                title=f"Synthetic {kind}",
                tags=["\u0065\u0301", "é", kind],
            )
            for kind, source_kind in cases
        ]

        raw = source.read_bytes()
        self.assertEqual(len({item["item_id"] for item in items}), 5)
        self.assertEqual(self.store.read_index()["revision"], 5)
        for item in items:
            with self.subTest(kind=item["kind"]):
                self.assertEqual(item["source_sha256"], hashlib.sha256(raw).hexdigest())
                self.assertEqual(item["content_sha256"], hashlib.sha256(raw).hexdigest())
                self.assertEqual((self.store.root / item["content_path"]).read_bytes(), raw)
                self.assertEqual(item["tags"], sorted(set(item["tags"])))
                self.assertIn("é", item["tags"])

    def test_material_dedupes_by_kind_normalized_hash_and_source_identity(self):
        self.store.initialize()
        source = self.write_material("duplicate.md", "Orbit 17\n")
        first = self.add_material(source)
        before = self.store.read_index()
        duplicate = self.add_material(source, title="Ignored duplicate title")
        cross_identity = self.add_material(source, source_kind="user_confirmed")
        cross_kind = self.add_material(source, kind="opinions")

        self.assertEqual(duplicate, first)
        self.assertEqual(self.store.read_index()["revision"], before["revision"] + 2)
        self.assertNotEqual(cross_identity["item_id"], first["item_id"])
        self.assertNotEqual(cross_kind["item_id"], first["item_id"])

    def test_material_rejects_invalid_source_and_non_user_experience(self):
        self.store.initialize()
        invalid_utf8 = self.write_material("invalid.md", b"\xff")
        empty = self.write_material("empty.md", "")

        self.assert_error_code(
            "invalid_input",
            lambda: self.add_material(Path(self.temporary.name) / "missing.md"),
        )
        self.assert_error_code("invalid_input", lambda: self.add_material(invalid_utf8))
        self.assert_error_code("invalid_input", lambda: self.add_material(empty))
        valid = self.write_material("valid.md", "synthetic")
        self.assert_error_code(
            "invalid_input",
            lambda: self.add_material(valid, source_kind="external_reference"),
        )
        self.assertEqual(self.store.read_index(), {"schema_version": 1, "revision": 0, "items": []})

    def test_material_import_rejects_symlinked_managed_directory(self):
        self.store.initialize()
        source = self.write_material("source.md", "synthetic")
        outside = Path(self.temporary.name) / "outside"
        outside.mkdir()
        (self.store.root / "knowledge").symlink_to(outside, target_is_directory=True)

        self.assert_error_code("path_escape", lambda: self.add_material(source))
        self.assertFalse(any(outside.iterdir()))

    def test_material_lifecycle_list_and_visibility_revisions(self):
        self.store.initialize()
        source = self.write_material("lifecycle.md", "Orbit agent lifecycle material")
        item = self.add_material(source, visibility="private", tags=["agent", "orbit"])

        self.assertEqual([entry["item_id"] for entry in self.store.list_materials(kind="experiences")], [item["item_id"]])
        disabled = self.store.set_material_status(item["item_id"], "disabled")
        self.assertEqual((disabled["status"], disabled["revision"]), ("disabled", 2))
        self.assertEqual(self.store.list_materials(status="disabled")[0]["item_id"], item["item_id"])
        self.assertEqual(self.store.set_material_status(item["item_id"], "disabled"), disabled)

        enabled = self.store.set_material_status(item["item_id"], "active")
        self.assertEqual((enabled["status"], enabled["revision"]), ("active", 3))
        publishable = self.store.set_material_visibility(
            item["item_id"], "publishable", expected_revision=3
        )
        self.assertEqual((publishable["visibility"], publishable["revision"]), ("publishable", 4))
        self.assert_error_code(
            "revision_conflict",
            lambda: self.store.set_material_visibility(item["item_id"], "private", expected_revision=3),
        )
        self.assertEqual(self.store.list_materials()[0]["visibility"], "publishable")

    def test_search_uses_query_content_filters_disabled_and_stably_orders_ties(self):
        self.store.initialize()
        orbit = self.add_material(
            self.write_material("orbit.md", "Orbit Agent protocol with evidence marker"),
            title="Orbit Agent",
            summary="Agent evidence",
            tags=["agent", "orbit"],
        )
        chinese = self.add_material(
            self.write_material("chinese.md", "轨道方案包含独特上下文"),
            kind="opinions",
            title="轨道方案",
            source_kind="user_confirmed",
            source_ref="synthetic://chinese",
            visibility="publishable",
            tags=["中文"],
        )
        tie_a = self.add_material(
            self.write_material("tie-a.md", "signal"),
            kind="cases",
            title="Signal",
            source_ref="synthetic://tie-a",
            visibility="publishable",
        )
        tie_b = self.add_material(
            self.write_material("tie-b.md", "signal"),
            kind="previous_articles",
            title="Signal",
            source_ref="synthetic://tie-b",
            visibility="publishable",
        )

        english = self.store.search_materials("orbit agent")
        self.assertEqual(english[0]["item_id"], orbit["item_id"])
        self.assertGreater(english[0]["score"], 0)
        self.assertNotIn("content", english[0])
        self.assertEqual(
            self.store.search_materials("orbit", tag="agent")[0]["item_id"],
            orbit["item_id"],
        )
        self.assertEqual(self.store.search_materials("orbit", tag="missing"), [])
        self.assertEqual(self.store.search_materials("轨道")[0]["item_id"], chinese["item_id"])
        self.assertEqual(self.store.search_materials("does-not-exist"), [])
        ties = self.store.search_materials("signal")
        tie_ids = [entry["item_id"] for entry in ties if entry["item_id"] in {tie_a["item_id"], tie_b["item_id"]}]
        self.assertEqual(tie_ids, sorted(tie_ids))

        self.store.set_material_status(orbit["item_id"], "disabled")
        self.assertNotIn(orbit["item_id"], [entry["item_id"] for entry in self.store.search_materials("orbit")])
        self.assertEqual(
            [entry["item_id"] for entry in self.store.search_materials("signal", kind="cases", limit=1)],
            [tie_a["item_id"]],
        )

    def test_task_approval_is_idempotent_scoped_and_rejects_private_or_disabled_items(self):
        self.store.initialize()
        ask = self.add_material(
            self.write_material("ask.md", "ask before use"),
            visibility="ask_before_use",
        )
        private = self.add_material(
            self.write_material("private.md", "private"),
            kind="opinions",
            visibility="private",
        )
        publishable = self.add_material(
            self.write_material("publishable.md", "publishable"),
            kind="cases",
            visibility="publishable",
        )
        run = self.run_directory()

        self.assert_error_code(
            "privacy_unapproved",
            lambda: self.store.admit_material(run, ask["item_id"], purpose="background"),
        )
        self.assertEqual(
            self.store.admit_material(run, publishable["item_id"], purpose="quote")[1],
            {"status": "not_required"},
        )
        approved = self.store.approve(run, ask["item_id"], allowed_use="background")
        self.assertEqual(approved, self.store.approve(run, ask["item_id"], allowed_use="background"))
        log = json.loads((run / "context-approvals.json").read_text(encoding="utf-8"))
        self.assertEqual((log["task_id"], log["revision"]), ("TASK-001", 1))
        self.assertEqual(approved["approval_sha256"], personal_context.canonical_sha256({
            key: value for key, value in approved.items() if key != "approval_sha256"
        }))
        self.assert_error_code(
            "privacy_unapproved",
            lambda: self.store.approve(run, private["item_id"], allowed_use="background"),
        )
        self.assert_error_code(
            "privacy_unapproved",
            lambda: self.store.admit_material(run, private["item_id"], purpose="background"),
        )
        self.assertEqual(
            self.store.admit_material(run, ask["item_id"], purpose="background")[1],
            approved,
        )
        self.store.set_material_status(ask["item_id"], "disabled")
        self.assert_error_code(
            "disabled",
            lambda: self.store.approve(run, ask["item_id"], allowed_use="quote"),
        )
        self.assert_error_code(
            "disabled",
            lambda: self.store.admit_material(run, ask["item_id"], purpose="background"),
        )

    def test_different_home_concurrent_approvals_preserve_both_revisions(self):
        context = multiprocessing.get_context("fork")
        run = self.run_directory("TASK-APPROVAL-RACE")
        homes = [Path(self.temporary.name) / name for name in ("home-a", "home-b")]
        item_ids = []
        for index, home in enumerate(homes):
            store = ContextStore(home)
            store.initialize()
            source = self.write_material(f"approval-race-{index}.md", f"approval race {index}")
            item = store.add_material(
                source,
                kind="experiences",
                title=f"Approval race {index}",
                source_kind="user_provided",
                source_ref=f"synthetic://approval-race-{index}",
                visibility="ask_before_use",
            )
            item_ids.append(item["item_id"])

        barrier = context.Barrier(2)
        results = context.Queue()
        processes = [
            context.Process(
                target=_approve_competing_material,
                args=(str(home), str(run), item_id, barrier, results),
            )
            for home, item_id in zip(homes, item_ids)
        ]
        for process in processes:
            self.addCleanup(lambda process=process: process.is_alive() and process.terminate())
            process.start()
        for process in processes:
            process.join(5)
            self.assertEqual(process.exitcode, 0)

        outcomes = [results.get(timeout=2) for _ in processes]
        self.assertEqual([outcome[0] for outcome in outcomes], ["ok", "ok"])
        stored = json.loads((run / "context-approvals.json").read_text(encoding="utf-8"))
        self.assertEqual(stored["revision"], 2)
        self.assertEqual(
            {approval["item_id"] for approval in stored["approvals"]},
            set(item_ids),
        )

    def test_explicit_legacy_import_is_idempotent_and_keeps_per_file_failures(self):
        legacy = Path(self.temporary.name) / "legacy"
        experiences = legacy / "experiences"
        experiences.mkdir(parents=True)
        (experiences / "a.md").write_text("legacy synthetic", encoding="utf-8")
        (experiences / "duplicate.md").write_text("legacy synthetic", encoding="utf-8")
        (experiences / "broken.md").write_bytes(b"\xff")
        self.store.initialize()
        self.assertEqual(self.store.read_index(), {"schema_version": 1, "revision": 0, "items": []})

        first = self.store.import_legacy(legacy)
        self.assertEqual(len(first["imported"]), 1)
        self.assertEqual(len(first["skipped"]), 1)
        self.assertEqual(first["failed"], [{"path": "experiences/broken.md", "error": {"code": "invalid_input"}}])
        item = self.store.list_materials()[0]
        self.assertEqual((item["ingest_kind"], item["source_kind"], item["visibility"]), (
            "legacy_import", "user_provided", "private"
        ))
        self.assertEqual(self.store.read_index()["revision"], 1)

        second = self.store.import_legacy(legacy)
        self.assertEqual(second["imported"], [])
        self.assertEqual(self.store.read_index()["revision"], 1)

    def test_snapshot_is_immutable_and_enforces_private_and_approval_admission(self):
        self.store.initialize()
        first_profile = self.store.update_profile(self.confirmed_profile(), expected_revision=0)
        ask = self.add_material(
            self.write_material("snapshot-ask.md", "approved snapshot source"),
            visibility="ask_before_use",
        )
        publishable = self.add_material(
            self.write_material("snapshot-public.md", "publishable snapshot source"),
            kind="opinions",
            visibility="publishable",
        )
        private = self.add_material(
            self.write_material("snapshot-private.md", "private snapshot source"),
            kind="cases",
            visibility="private",
        )
        run = self.run_directory()
        self.store.approve(run, ask["item_id"], allowed_use="background")

        snapshot = self.store.create_snapshot(run, materials=[
            (publishable["item_id"], "quote"),
            (ask["item_id"], "background"),
        ])
        before = (run / "personal-context-snapshot.json").read_bytes()
        self.assertEqual(snapshot["profile"]["revision"], first_profile["revision"])
        self.assertEqual(
            [(entry["item_id"], entry["purpose"]) for entry in snapshot["materials"]],
            sorted([(publishable["item_id"], "quote"), (ask["item_id"], "background")]),
        )
        self.assertNotIn("source_ref", snapshot["materials"][0]["metadata"])
        for entry in snapshot["materials"]:
            self.assertEqual(
                (run / entry["copy_path"]).read_bytes(),
                (self.store.root / f"knowledge/{entry['kind']}/{entry['item_id']}/content.md").read_bytes(),
            )
        self.assertEqual(
            self.store.create_snapshot(run, materials=[
                (ask["item_id"], "background"),
                (publishable["item_id"], "quote"),
            ]),
            snapshot,
        )
        self.assert_error_code(
            "snapshot_conflict",
            lambda: self.store.create_snapshot(run, materials=[(publishable["item_id"], "quote")]),
        )

        self.store.update_profile(
            self.confirmed_profile(values=["evidence first", "new global value"]),
            expected_revision=1,
        )
        self.assertEqual((run / "personal-context-snapshot.json").read_bytes(), before)
        newer_run = self.run_directory("TASK-002")
        newer = self.store.create_snapshot(newer_run, materials=[(publishable["item_id"], "quote")])
        self.assertEqual(newer["profile"]["revision"], 2)
        self.store.set_material_visibility(publishable["item_id"], "private", expected_revision=1)
        self.assertEqual((run / "personal-context-snapshot.json").read_bytes(), before)

        unapproved_run = self.run_directory("TASK-003")
        self.assert_error_code(
            "privacy_unapproved",
            lambda: self.store.create_snapshot(unapproved_run, materials=[(ask["item_id"], "quote")]),
        )
        self.assert_error_code(
            "privacy_unapproved",
            lambda: self.store.create_snapshot(unapproved_run, materials=[(private["item_id"], "background")]),
        )

    def test_different_home_conflicting_snapshots_have_one_winner(self):
        context = multiprocessing.get_context("fork")
        run = self.run_directory("TASK-SNAPSHOT-RACE")
        homes = [Path(self.temporary.name) / name for name in ("snapshot-home-a", "snapshot-home-b")]
        item_ids = []
        for index, home in enumerate(homes):
            store = ContextStore(home)
            store.initialize()
            source = self.write_material(f"snapshot-race-{index}.md", f"snapshot race {index}")
            item = store.add_material(
                source,
                kind="experiences",
                title=f"Snapshot race {index}",
                source_kind="user_provided",
                source_ref=f"synthetic://snapshot-race-{index}",
                visibility="publishable",
            )
            item_ids.append(item["item_id"])

        barrier = context.Barrier(2)
        results = context.Queue()
        processes = [
            context.Process(
                target=_create_competing_snapshot,
                args=(str(home), str(run), item_id, barrier, results),
            )
            for home, item_id in zip(homes, item_ids)
        ]
        for process in processes:
            self.addCleanup(lambda process=process: process.is_alive() and process.terminate())
            process.start()
        for process in processes:
            process.join(5)
            self.assertEqual(process.exitcode, 0)

        outcomes = [results.get(timeout=2) for _ in processes]
        self.assertCountEqual([outcome[0] for outcome in outcomes], ["ok", "error"])
        self.assertEqual([outcome[1] for outcome in outcomes if outcome[0] == "error"], ["snapshot_conflict"])
        successful = next(outcome[1] for outcome in outcomes if outcome[0] == "ok")
        stored = json.loads((run / "personal-context-snapshot.json").read_text(encoding="utf-8"))
        self.assertEqual(stored, successful)

    def test_context_usage_is_write_once_and_verify_run_checks_copies_and_artifacts(self):
        self.store.initialize()
        item = self.add_material(
            self.write_material("usage.md", "usage marker"),
            visibility="publishable",
        )
        run = self.run_directory()
        snapshot = self.store.create_snapshot(run, materials=[(item["item_id"], "background")])
        (run / "final.md").write_text("final uses usage marker", encoding="utf-8")
        (run / "acceptance-report.md").write_text("accepted", encoding="utf-8")
        uses = [{"item_id": item["item_id"], "purpose": "background", "section": "opening", "claim_id": "claim-001"}]
        usage = self.store.record_usage(
            run,
            uses=uses,
            artifact_paths={"final": "final.md", "acceptance": "acceptance-report.md"},
        )
        self.assertEqual(
            self.store.record_usage(
                run,
                uses=uses,
                artifact_paths={"final": "final.md", "acceptance": "acceptance-report.md"},
            ),
            usage,
        )
        verified = self.store.verify_run(run)
        self.assertEqual((verified["verified"], verified["snapshot_sha256"]), (True, snapshot["snapshot_sha256"]))
        self.assert_error_code(
            "duplicate",
            lambda: self.store.record_usage(
                run,
                uses=[],
                artifact_paths={"final": "final.md", "acceptance": "acceptance-report.md"},
            ),
        )
        (run / "final.md").write_text("tampered", encoding="utf-8")
        self.assert_error_code("hash_mismatch", lambda: self.store.verify_run(run))

    def test_context_usage_competing_writes_have_one_winner(self):
        self.store.initialize()
        item = self.add_material(
            self.write_material("usage-race.md", "usage race marker"),
            visibility="publishable",
        )
        run = self.run_directory("TASK-USAGE-RACE")
        self.store.create_snapshot(run, materials=[(item["item_id"], "background")])
        (run / "final.md").write_text("final", encoding="utf-8")
        (run / "acceptance-report.md").write_text("accepted", encoding="utf-8")
        barrier = multiprocessing.Barrier(2)
        results = multiprocessing.Queue()
        contenders = [
            [{"item_id": item["item_id"], "purpose": "background", "section": section, "claim_id": claim_id}]
            for section, claim_id in (("opening", "claim-a"), ("closing", "claim-b"))
        ]
        processes = [
            multiprocessing.Process(
                target=_record_competing_context_usage,
                args=(str(self.home), str(run), uses, barrier, results),
            )
            for uses in contenders
        ]
        for process in processes:
            process.start()
        for process in processes:
            process.join(5)
            self.assertEqual(process.exitcode, 0)
        outcomes = [results.get(timeout=2) for _ in processes]
        self.assertCountEqual([outcome[0] for outcome in outcomes], ["ok", "error"])
        self.assertEqual([outcome[1] for outcome in outcomes if outcome[0] == "error"], ["duplicate"])
        successful_uses = next(outcome[1] for outcome in outcomes if outcome[0] == "ok")
        stored = json.loads((run / "context-usage.json").read_text(encoding="utf-8"))
        self.assertEqual(stored["uses"], successful_uses)
        self.assertTrue(self.store.verify_run(run)["verified"])

    def test_safe_path_rejects_absolute_parent_and_symlink_escapes(self):
        root = self.store.root
        root.mkdir(parents=True)
        outside = Path(self.temporary.name) / "outside"
        outside.mkdir()
        (root / "escape").symlink_to(outside, target_is_directory=True)

        for relative in ("/absolute", "../outside", "escape/file.json"):
            with self.subTest(relative=relative):
                self.assert_error_code("path_escape", lambda: safe_path(root, relative))

    def test_fcntl_lock_serializes_independent_processes(self):
        if not Path("/proc/locks").is_file():
            self.skipTest("Linux /proc/locks is required to observe a blocked flock")
        context = multiprocessing.get_context("fork")
        entered = context.Event()
        release = context.Event()
        contender_acquired = context.Event()
        holder = context.Process(
            target=_hold_context_lock,
            args=(str(self.home), entered, release),
        )
        contender = context.Process(
            target=_take_context_lock,
            args=(str(self.home), contender_acquired),
        )
        self.addCleanup(lambda: holder.is_alive() and holder.terminate())
        self.addCleanup(lambda: contender.is_alive() and contender.terminate())

        holder.start()
        self.assertTrue(entered.wait(3), "holder did not acquire the lock")
        contender.start()
        try:
            self.assertTrue(
                _wait_for_flock_waiter(self.store.root / ".personal-context.lock", contender.pid),
                "contender did not block on the holder's flock",
            )
            self.assertFalse(contender_acquired.is_set(), "contender acquired before holder release")
        finally:
            release.set()
            holder.join(3)
            contender.join(3)

        self.assertEqual(holder.exitcode, 0)
        self.assertEqual(contender.exitcode, 0)
        self.assertTrue(contender_acquired.is_set(), "contender did not acquire after holder release")


if __name__ == "__main__":
    unittest.main()
