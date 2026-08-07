import hashlib
import json
import unittest
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/personal-context/contract-v1.json"
# CONTRACT reference removed - proposal docs deleted
MATERIAL = ROOT / "tests/fixtures/personal-context/orbit-17.md"


def canonical_hash(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def normalized_content_hash(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value).replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class PersonalContextContractTests(unittest.TestCase):
    def setUp(self):
        self.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_empty_profile_and_style_are_canonical_documents(self):
        for name, payload_fields in (
            ("empty_profile", ("identity", "expertise", "content_directions", "values", "expression", "avoid", "provenance")),
            ("empty_style", ("rules", "provenance")),
        ):
            with self.subTest(name=name):
                document = self.fixture[name]
                self.assertEqual(document["schema_version"], 1)
                self.assertEqual(document["status"], "empty")
                self.assertEqual(document["revision"], 0)
                self.assertFalse(any(value is None for value in document.values()))
                self.assertEqual(
                    document["content_sha256"],
                    canonical_hash({field: document[field] for field in payload_fields}),
                )

    def test_ready_profile_hashes_only_confirmed_content(self):
        document = self.fixture["ready_profile"]
        payload_fields = ("identity", "expertise", "content_directions", "values", "expression", "avoid", "provenance")

        self.assertEqual(document["schema_version"], 1)
        self.assertEqual(document["status"], "ready")
        self.assertEqual(document["profile_id"], "author-default")
        self.assertEqual(document["revision"], 1)
        self.assertEqual(document["provenance"], {"kind": "user_confirmed"})
        self.assertEqual(
            document["content_sha256"],
            canonical_hash({field: document[field] for field in payload_fields}),
        )

    def test_runtime_examples_share_schema_and_error_names(self):
        fixture = self.fixture
        for name in ("empty_knowledge_index", "knowledge_index", "knowledge_item", "approval_log", "snapshot", "context_usage"):
            with self.subTest(name=name):
                self.assertEqual(fixture[name]["schema_version"], 1)

        self.assertEqual(fixture["empty_knowledge_index"], {"schema_version": 1, "revision": 0, "items": []})
        normalization = fixture["normalization"]
        self.assertEqual(normalization["normalized_content_sha256"], normalized_content_hash(normalization["input"]))

        item = fixture["knowledge_item"]
        raw_material = MATERIAL.read_bytes()
        self.assertEqual(item["source_sha256"], hashlib.sha256(raw_material).hexdigest())
        self.assertEqual(item["content_sha256"], hashlib.sha256(raw_material).hexdigest())
        self.assertEqual(item["normalized_content_sha256"], normalized_content_hash(raw_material.decode("utf-8")))
        approval = fixture["approval_log"]["approvals"][0]
        self.assertEqual(approval["allowed_use"], "background")
        self.assertEqual(
            approval["approval_sha256"],
            canonical_hash({key: value for key, value in approval.items() if key != "approval_sha256"}),
        )
        snapshot = fixture["snapshot"]
        self.assertEqual(snapshot["style"]["status"], "empty")
        for context in (snapshot["profile"], snapshot["style"]):
            self.assertEqual(context["content_sha256"], canonical_hash(context["content"]))
        material = snapshot["materials"][0]
        self.assertEqual(material["metadata_sha256"], canonical_hash(material["metadata"]))
        self.assertNotIn("source_ref", material["metadata"])
        self.assertEqual(
            set(material["metadata"]),
            {"schema_version", "item_id", "revision", "kind", "status", "title", "summary", "tags", "source_kind", "ingest_kind", "visibility"},
        )
        self.assertEqual(material["approval"]["allowed_use"], "background")
        self.assertEqual(material["approval"], approval)
        self.assertEqual(
            snapshot["snapshot_sha256"],
            canonical_hash({key: value for key, value in snapshot.items() if key != "snapshot_sha256"}),
        )
        self.assertEqual(fixture["knowledge_item"]["ingest_kind"], "managed_add")
        self.assertNotEqual(fixture["knowledge_item"]["source_kind"], "legacy_import")
        self.assertEqual(fixture["context_usage"]["uses"][0]["purpose"], "background")
        for name, artifact in fixture["context_usage"]["artifacts"].items():
            with self.subTest(artifact=name):
                self.assertEqual(
                    artifact["sha256"],
                    hashlib.sha256((MATERIAL.parent / artifact["path"]).read_bytes()).hexdigest(),
                )

    @unittest.skip("Proposal doc removed during cleanup")
    def test_contract_names_fixture_fields_and_failure_codes(self):
        contract = CONTRACT.read_text(encoding="utf-8")
        for field in (
            "schema_version", "profile_id", "revision", "content_sha256", "normalized_content_sha256",
            "allowed_use", "approval_sha256", "snapshot_sha256", "context-usage.json", "ingest_kind",
            "task-safe metadata projection", "NFC", "hash_mismatch", "invalid_input", "allow_nan=False",
        ):
            self.assertIn(f"`{field}`", contract)
        for error_code in (
            "not_initialized", "invalid_json", "schema_unsupported", "revision_conflict", "path_escape",
            "duplicate", "unknown_id", "disabled", "privacy_unapproved", "snapshot_conflict",
        ):
            self.assertIn(f"`{error_code}`", contract)


if __name__ == "__main__":
    unittest.main()
