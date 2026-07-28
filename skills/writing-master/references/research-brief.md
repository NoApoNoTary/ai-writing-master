# Context-aware Research Brief

## Purpose

`research-brief-draft.json` is the Researcher output for Manifest phase `topic_research`. It ranks 3–10 candidate topics from current, task-relevant evidence. The Runtime later binds it to the task `brief.md` and frozen `personal-context-snapshot.json` as `research-brief.json`.

This is Topic Research, not Article Research. Its Evidence supports candidate ranking and topic rationale only; it is not an accepted article claim and does not automatically enter `claims.yaml`.

## Allowed inputs

Read only the Manifest `allowed_inputs`:

- `brief.md`
- `personal-context-snapshot.json`
- Manifest-listed `context-materials/ITEM_ID.md`
- current live retrieval results
- this reference

Do not read the global Personal Context store. The Snapshot freezes the profile revision/hash and the only selected Material IDs eligible for `author_fit` references.

## Draft shape

The draft contains no task ID, runtime timestamp, input hashes, or document self-hash. The example below shows one candidate object for readability; a valid draft repeats this complete object 3–10 times with unique `candidate_id` values:

```json
{
  "schema_version": 1,
  "candidates": [
    {
      "candidate_id": "topic-001",
      "topic": "Candidate topic",
      "heat": {
        "score": 8.5,
        "basis": "Why current sources make this timely",
        "as_of": "2026-07-27T12:00:00+00:00",
        "evidence_ids": ["evidence-685efbbf930eb8af"]
      },
      "audience": "Specific intended readers",
      "angle": "A concrete decision lens",
      "evidence": [
        {
          "evidence_id": "evidence-685efbbf930eb8af",
          "source_url": "https://example.test/research/agent-browser-1",
          "source_title": "Synthetic Agent Browser Report 1",
          "publisher": "Synthetic Research",
          "source_date": "2026-07-27",
          "observed_at": "2026-07-27T11:30:00+00:00",
          "evidence_text": "Synthetic research evidence 1: recent browser execution capability evidence.",
          "content_sha256": "063e1bbd5b33324ed4f6739ecf6c286bb8fdceffe784e55726dede90febc412a"
        }
      ],
      "scores": {
        "heat": {"value": 8.5, "rationale": "Reason"},
        "user_value": {"value": 8.0, "rationale": "Reason"},
        "differentiation": {"value": 7.5, "rationale": "Reason"},
        "author_fit": {
          "value": 5.0,
          "rationale": "The frozen profile is empty, so author-fit confidence is limited.",
          "references": [
            {
              "kind": "profile",
              "profile_id": "author-default",
              "revision": 0,
              "content_sha256": "eb7877b5514de357ac7596eb7f894c85985b67f0e1ff39158d1f2cb121351452"
            }
          ]
        }
      },
      "rationale": "Overall recommendation rationale"
    }
  ]
}
```

For each candidate provide a non-empty Topic, Heat, Audience, Angle, Evidence, all four Scores, and Rationale. Scores are finite values in `0..10`; `heat.score` equals `scores.heat.value`. Candidate order is the recommendation order.

## Evidence and time discipline

Each Evidence object contains a source URL/title/publisher/date, an observed timestamp, verbatim or faithfully extracted evidence text, and its normalized content SHA-256. Use absolute `http` or `https` URLs. `heat.as_of` and `observed_at` are timezone-bearing RFC3339 timestamps; evidence is observed no later than the candidate Heat time, and `source_date` is no later than its UTC date.

Evidence IDs are deterministic:

```text
evidence- + SHA256(canonical JSON of source_url, source_date, content_sha256)[:16]
```

Only list Evidence IDs belonging to the same candidate in `heat.evidence_ids`. Do not claim that Runtime verifies an external source's continuing availability or semantic truth.

## Author fit

Every candidate has at least one `author_fit.references` entry. It may refer only to:

- the frozen Snapshot profile, using exactly its `profile_id`, `revision`, and `content_sha256`; or
- a selected Snapshot Material by `item_id`.

An empty profile (`revision: 0`) remains a valid reference. Explain the information limitation in the Agent rationale; do not invent author expertise.

## Missing live retrieval

The Host checks current web retrieval before preparing or dispatching a `topic_research` Handoff. If it is unavailable, the Lead records this pre-dispatch capability response:

```json
{
  "status": "blocked",
  "code": "realtime_research_unavailable",
  "missing_capability": "web_search"
}
```

This three-field object is not a Handoff Result and is never written to the Manifest `result_path`. No Handoff, `research-brief-draft.json`, or `research-brief.json` is created, and Heat is not inferred from stale local context.

## Decision boundary

Researcher 可以提出多个候选 Angle，但不选择最终角度。用户或 Lead 选定 candidate 后，Article Research 才生成 `sources.yaml`、`claims.yaml`、`asset-manifest.yaml` 和 `research-summary.md`。
