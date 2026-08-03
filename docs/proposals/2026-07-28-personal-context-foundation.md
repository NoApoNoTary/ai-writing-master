# Personal Context Foundation Runtime Contract

- Status: Goal A contract, implementation pending T11–T32
- Scope: Author Profile, five Knowledge Item kinds, task approvals, immutable snapshots and context usage
- Runtime format: JSON schema v1 plus UTF-8 Markdown/plain-text material bodies

This document is the canonical Goal A data contract. It defines deterministic Runtime data only; Agent prompts decide relevance and prose, while Runtime validates schemas, IDs, revisions, hashes, paths, approval and snapshot state.

## 1. Canonical JSON and shared rules

- Every Runtime JSON document has `schema_version: 1`.
- Every mutable aggregate has integer `revision`, beginning at `0` for a canonical empty state and otherwise increasing exactly once per successful write.
- Canonical JSON bytes use UTF-8, `ensure_ascii=False`, `allow_nan=False`, lexicographically sorted keys and separators `,` / `:`. A `content_sha256`, `metadata_sha256`, `approval_sha256` or `snapshot_sha256` is the SHA-256 of the documented canonical payload excluding that self-hash field.
- Imported material must be non-empty and decode as strict UTF-8. `normalized_content_sha256` hashes Unicode `NFC` text after CRLF/CR are converted to LF; no trimming or whitespace collapse occurs. `content.md` is a byte-for-byte managed copy of the validated UTF-8 source, so `source_sha256` and `content_sha256` initially match. Tags are NFC-normalized, deduplicated and lexicographically sorted. Index item IDs and Snapshot materials are sorted deterministically by ID (then purpose for materials). Profile preference arrays preserve confirmed user input order.
- Runtime paths are slash-separated, non-empty relative paths beneath their declared root. Absolute paths, `.` / `..`, and symlink escapes fail validation.
- Validation, revision, hash, path, approval and snapshot failures do not replace the last valid JSON document. CLI callers receive a non-zero exit.
- T10 fixtures use only synthetic data. They demonstrate field names, not a writing-quality claim.

## 2. Storage layout

```text
${WRITING_MASTER_HOME}/
└── personal-context/
    ├── author-profile.json
    ├── style-profile.json
    ├── knowledge-index.json
    └── knowledge/{kind}/{item_id}/
        ├── metadata.json
        └── content.md

${WRITING_MASTER_HOME}/runs/{task_id}/
├── context-approvals.json
├── personal-context-snapshot.json
├── context-materials/{item_id}.md
└── context-usage.json
```

`initialize()` creates `personal-context/` and its canonical empty Profile, Style and Index documents. It never scans or imports `personal_materials/`; that is an explicit T22 operation.

## 3. Profile and Style

### 3.1 Author Profile

The stable `profile_id` is `author-default`. A ready profile contains only explicitly supplied or confirmed identity data:

```json
{
  "schema_version": 1,
  "status": "ready",
  "profile_id": "author-default",
  "revision": 1,
  "updated_at": "2026-07-28T00:00:00+00:00",
  "identity": {"display_name": "ROLE_A"},
  "expertise": ["AI Agent"],
  "content_directions": ["software development"],
  "values": ["evidence first"],
  "expression": {"tone": ["analytical", "concise"]},
  "avoid": ["generic summaries"],
  "provenance": {"kind": "user_confirmed"},
  "content_sha256": "…"
}
```

Its `content_sha256` covers `identity`, `expertise`, `content_directions`, `values`, `expression`, `avoid` and `provenance`. `update_profile(expected_revision)` requires an exact current revision; a stale write returns `revision_conflict` and preserves the newer document.

The only no-profile representation is this canonical object, never a missing file or `null`:

```json
{
  "schema_version": 1,
  "status": "empty",
  "profile_id": "author-default",
  "revision": 0,
  "identity": {},
  "expertise": [],
  "content_directions": [],
  "values": [],
  "expression": {"tone": []},
  "avoid": [],
  "provenance": {"kind": "empty"},
  "content_sha256": "eb7877b5514de357ac7596eb7f894c85985b67f0e1ff39158d1f2cb121351452"
}
```

### 3.2 Style Profile in Goal A

Goal A creates only the canonical empty Style document:

```json
{
  "schema_version": 1,
  "status": "empty",
  "profile_id": "style-default",
  "revision": 0,
  "rules": [],
  "provenance": {"kind": "empty"},
  "content_sha256": "e11311951da1bacb28a2dda57b6c4be4d7f4baffe1a3b6ce07bb770d80ac1ff0"
}
```

No Style Observation, mutation, aggregation or `learn` CLI belongs to Goal A. Snapshot creation records this exact empty Style state until Goal B changes the contract.

## 4. Knowledge Item and index

Allowed `kind` values are `experiences`, `opinions`, `cases`, `references` and `previous_articles`. `status` is `active | disabled`; `visibility` is `private | publishable | ask_before_use`.

`knowledge-index.json` is the mutable aggregate:

```json
{"schema_version": 1, "revision": 1, "items": ["knowledge-orbit-17"]}
```

The only empty Index representation is `{"schema_version": 1, "revision": 0, "items": []}`.

Each managed item has `metadata.json` with this schema:

```json
{
  "schema_version": 1,
  "item_id": "knowledge-orbit-17",
  "revision": 1,
  "kind": "experiences",
  "status": "active",
  "title": "…",
  "summary": "…",
  "tags": ["…"],
  "source_kind": "user_provided",
  "ingest_kind": "managed_add",
  "source_ref": "…",
  "source_sha256": "…",
  "normalized_content_sha256": "…",
  "content_sha256": "…",
  "content_path": "knowledge/experiences/knowledge-orbit-17/content.md",
  "visibility": "ask_before_use",
  "created_at": "RFC3339",
  "updated_at": "RFC3339"
}
```

The dedupe key is exactly `(kind, normalized_content_sha256, source_kind)` and is computed by Runtime rather than persisted as a second mutable field. A duplicate under the same key is idempotent; identical bytes with another `kind` or `source_kind` remain distinct items. The Runtime computes both raw `source_sha256` and normalized UTF-8 `normalized_content_sha256`; it copies the material body into managed storage.

`summary` is always a string. T20 import may persist `""` when the caller supplied no summary; Runtime never invents a summary from source text. `tags` may likewise be an empty list.

`source_kind` preserves source identity: `user_provided`, `user_confirmed`, `external_reference` or `editorial_inference`. `ingest_kind` records `managed_add | legacy_import` without changing source identity or the dedupe key. `experiences` cannot be claimed from `external_reference` or `editorial_inference`; a model summary remains an inference/reference rather than a user experience.

Each Snapshot material embeds a `task-safe metadata projection`: `schema_version`, `item_id`, `revision`, `kind`, `status`, `title`, `summary`, `tags`, `source_kind`, `ingest_kind` and `visibility`. `metadata_sha256` hashes this exact projection. It deliberately excludes `source_ref`, source/content hashes, `content_path`, timestamps and any global path so Deep Manifest inputs do not leak the personal-context directory.

### 4.1 Mutation and ordering semantics

- A Profile update requires exact `expected_revision`. If its canonical content is unchanged, it returns the existing Profile without a revision increment; a changed accepted payload increments revision by one. A stale expected revision always returns `revision_conflict`.
- Material bodies are immutable after managed import. Lifecycle and visibility changes create a new Item metadata revision; the Index revision changes only when item membership changes. `knowledge-index.json.items` is sorted by `item_id`.
- Approvals are append-only. Repeating the same `(task_id, item_id, allowed_use)` approval returns the existing approval without changing the approval-log revision; a new allowed use appends one approval and increments that revision.
- A Snapshot and a completed Usage record are write-once. Repeating the same canonical object is idempotent; different bytes for the same task return `snapshot_conflict` or `duplicate` respectively. Snapshot materials are sorted by `(item_id, purpose)`, and a repeated pair is `duplicate`.

## 5. Task approval, Snapshot and Usage

### 5.1 Task Approval

`context-approvals.json` is scoped to one existing task:

```json
{
  "schema_version": 1,
  "task_id": "TASK-001",
  "revision": 1,
  "approvals": [
    {
      "approval_id": "approval-001",
      "item_id": "knowledge-orbit-17",
      "allowed_use": "background",
      "status": "approved",
      "approved_at": "RFC3339",
      "approval_sha256": "…"
    }
  ]
}
```

`allowed_use` is exactly `background | paraphrase | quote`. `approval_sha256` covers the approval object excluding itself. Approval requires the current task, an active existing item and one known purpose. `publishable` needs no approval; `ask_before_use` needs an approval matching the selected purpose; `private` always fails snapshot admission.

### 5.2 Immutable Snapshot

`personal-context-snapshot.json` fixes all global inputs for one run:

```json
{
  "schema_version": 1,
  "task_id": "TASK-001",
  "created_at": "RFC3339",
  "profile": {
    "status": "empty",
    "profile_id": "author-default",
    "revision": 0,
    "content": {"identity": {}, "expertise": [], "content_directions": [], "values": [], "expression": {"tone": []}, "avoid": [], "provenance": {"kind": "empty"}},
    "content_sha256": "…"
  },
  "style": {
    "status": "empty",
    "profile_id": "style-default",
    "revision": 0,
    "content": {"rules": [], "provenance": {"kind": "empty"}},
    "content_sha256": "…"
  },
  "materials": [
    {
      "item_id": "knowledge-orbit-17",
      "kind": "experiences",
      "metadata": {"schema_version": 1, "item_id": "knowledge-orbit-17", "revision": 1, "kind": "experiences", "status": "active", "title": "…", "summary": "…", "tags": ["…"], "source_kind": "user_provided", "ingest_kind": "managed_add", "visibility": "ask_before_use"},
      "metadata_sha256": "…",
      "content_sha256": "…",
      "purpose": "background",
      "approval": {"approval_id": "approval-001", "item_id": "knowledge-orbit-17", "allowed_use": "background", "status": "approved", "approved_at": "RFC3339", "approval_sha256": "…"},
      "copy_path": "context-materials/knowledge-orbit-17.md"
    }
  ],
  "snapshot_sha256": "…"
}
```

Snapshot creation embeds frozen Profile/Style content because Standard consumes only the task Snapshot and task-local material copies. It also embeds the selected item metadata and the resolved approval value/hash (or `{"status":"not_required"}` for publishable material), so later global approval-log edits cannot rewrite historical admission. It copies every selected material to the task-local `context-materials/` path. Repeating an identical request is idempotent; a different request for the same task returns `snapshot_conflict`. Global profile/item/approval changes never mutate this snapshot or its copies.

### 5.3 Context Usage

`context-usage.json` proves recorded use, not semantic non-leakage:

```json
{
  "schema_version": 1,
  "task_id": "TASK-001",
  "snapshot_sha256": "…",
  "status": "complete",
  "uses": [
    {"item_id": "knowledge-orbit-17", "purpose": "background", "section": "opening", "claim_id": "claim-001"}
  ],
  "artifacts": {
    "final": {"path": "final.md", "sha256": "…"},
    "acceptance": {"path": "acceptance-report.md", "sha256": "…"}
  },
  "recorded_at": "RFC3339"
}
```

`verify-run` must confirm the snapshot hash, frozen Profile/Style content hashes, task-local material copies, item IDs, embedded metadata hashes, frozen approval values/hashes, `context-usage.json`, final/acceptance artifact hashes and each recorded purpose. It does not claim to semantically prove that private data never appears in prose.

Writing identical canonical usage data is idempotent; a competing different Usage record for the same completed task fails as `duplicate`. Usage always references the Snapshot hash it consumed.

Each `uses[]` record must reference one Snapshot material and its exact `purpose`; `section` is required, while `claim_id` is optional. Artifact paths are run-relative files and their hashes must recompute.

## 6. Stable failure codes

The Python module raises a structured Context error with one of these codes; the CLI emits a non-zero `{"error":{"code":"…","message":"…"}}` JSON object when JSON output is requested:

| Code | Meaning |
|---|---|
| `not_initialized` | Canonical context root or required empty document is absent. |
| `invalid_input` | Text, enum, ID, timestamp or other caller input is malformed. |
| `invalid_json` | JSON cannot be decoded or is not an object. |
| `schema_unsupported` | `schema_version` or required fields are incompatible. |
| `revision_conflict` | `expected_revision` differs from the latest document revision. |
| `path_escape` | A managed, run or input path is absolute, unsafe or escapes through a symlink. |
| `duplicate` | A non-idempotent duplicate request was attempted. |
| `unknown_id` | A requested item, approval or task reference is absent. |
| `disabled` | A disabled item was selected for a new Snapshot. |
| `privacy_unapproved` | Visibility or task approval does not allow the requested purpose. |
| `hash_mismatch` | A stored, copied, approved or referenced hash does not recompute. |
| `snapshot_conflict` | A task already owns a different immutable Snapshot. |

Additional implementation-specific errors may be introduced only when they preserve these categories and failure semantics; no failure may silently create a partial Profile, Item, Approval or Snapshot.

## 7. Goal A boundary

This contract adds no database, vector index, background process, cloud service or third-party runtime dependency. Context operations use an explicit `RUN_DIR`; they do not allocate task IDs, discover recent tasks, mutate `status.json`, implement generic resume, or change quick/standard/deep semantics. It does not silently migrate legacy materials, infer user identity from articles, write a Style Observation, or create a Research Brief.
