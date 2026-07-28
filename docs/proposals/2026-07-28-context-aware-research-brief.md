# Context-aware Research Brief Proposal

## Decision

Add a task-local, write-once Research Brief between a broad content contract and article fact research. The Researcher ranks 3–10 topical candidates with current Evidence, reader value, differentiation and Snapshot-bound author fit; Runtime validates document structure, time, hashes and references without claiming semantic truth.

## Boundary

The Brief consumes only `brief.md`, the task `personal-context-snapshot.json`, Manifest-listed task material copies and live retrieval results. It neither reads global Personal Context files nor changes the Snapshot, `status.json`, or article research artifacts.

`topic_research` produces `research-brief-draft.json`. After a candidate is selected, existing `research` produces `sources.yaml`, `claims.yaml`, `asset-manifest.yaml` and `research-summary.md`. Brief Evidence is not automatically an accepted article claim.

Live retrieval is a Host preflight gate. When it is missing, the three-field `realtime_research_unavailable` object is a pre-dispatch capability response, not an existing Handoff Result; no Handoff or Brief artifact is created. This preserves the current Handoff Result schema without changing Integration-owned Runtime files.

## Persistence

The Runtime anchors the run directory with a directory file descriptor, reads the task ID from `status.json`, hashes raw `brief.md` bytes, validates the frozen Snapshot, and atomically writes `research-brief.json` through that same anchor. Ancestor path retargeting therefore cannot redirect the write after validation. The document is idempotent for identical draft and input hashes; a different document for the same run is `duplicate`. Verification recomputes self, Brief, Snapshot and Evidence hashes.

## Deliberate non-goals

No network access in Runtime, background trend monitoring, automatic topic discovery, new Agent role, Brief revision history, or semantic endorsement of Agent scores is introduced.
