# Agent Instructions for Writing Master

**Purpose**: Guidelines for AI agents (Claude, GPT, etc.) working on this skill to prevent drift toward "证据审查系统" (evidence auditing system).

## Core Product Identity

You are implementing a **writing assistant for hot-topic speed writing**, not an investigative journalism tool or compliance system.

**Target experience**: User says "write an article about Claude 5 launch for WeChat" → System auto-researches → Writes in author's voice → User reviews → Publishes. Total time: 15-20 minutes.

## Critical Rule: Internal ≠ User-Facing

**Evidence tracking is quality infrastructure. It must NOT become visible product surface.**

### ✅ What to Keep (Internal)

- `sources.yaml` + `claims.yaml` for fact traceability
- Automatic fact verification during writing
- Multi-pass quality checks (accuracy, logic, readability)
- SHA-256 hashing, version control, snapshots
- State files in `runs/{task_id}/`

### ❌ What to Hide (User-Facing)

- **No** `claim_id` visible in articles or user outputs
- **No** YAML reports (`review-report.yaml`, `acceptance-report.yaml`) as deliverables
- **No** diagnostic codes (`WM-CAP-001`) or hash values in user messages
- **No** internal state fields: `persona_snapshot`, `voice_snapshot_sha256`, `mode_readiness`

**User sees**: "Article ready! Optional suggestions: paragraph 3 could be more specific..."  
**User does NOT see**: "evidence_layer: 85/100, claim_001: 来源可达性待验证"

## Language Guidelines

Use **creative/editorial language**, not compliance/auditing language:

| ❌ Avoid | ✅ Use Instead |
|---------|---------------|
| 验收 (acceptance inspection) | 定稿 (finalize) |
| 审计 (audit) | 审稿 (review) |
| 预检 (preflight check) | 准备 (prepare) |
| 批准 (approval) | 确认 (confirm) |
| 合同 (contract) | 方案 (plan) |
| Auditor (role name) | Editor / Reviewer |
| capability-preflight.md | setup.md |
| acceptance-report.yaml | final-check.md |

**Why this matters**: Words shape user perception. "验收" feels like homework submission; "定稿" feels like finishing creative work.

## Evidence Level Defaults

**When implementing writing flows, use the appropriate evidence level:**

```yaml
quick_draft:
  evidence_level: relaxed
  behavior: Prevent obvious fabrication only, prioritize speed
  output: 1 markdown file, not 7 YAMLs
  
standard_writing:
  evidence_level: balanced  # DEFAULT for hot-topics
  behavior: Verify core data automatically, allow opinions without sourcing
  output: Finished article + simple reference list (not claim-by-claim YAML)
  
deep_writing:
  evidence_level: strict
  behavior: Full source tracking for every key claim
  output: Article + detailed evidence documentation (for serious reports only)
```

**Current problem**: The skill applies `strict` behavior everywhere. Standard mode should use `balanced` by default.

**Hot-topic articles don't need**:
- Every sentence linked to `claim_id`
- Three-layer review with separate reports
- User confirmation of "素材接收", "内容契约", "大纲", "验收"
- Personal experiences and opinions logged as "evidence items"

## Implementation Patterns

### ✅ Good: Suggestions, Not Scores

```python
def review_article(draft):
    issues = check_accuracy_and_readability(draft)
    return format_as_plain_text_suggestions(issues)
    # Output: "Paragraph 3: consider being more specific..."
```

### ❌ Bad: Scores and Reports

```python
def review_article(draft):
    scores = {
        'evidence_layer': 85,
        'editing_layer': 90,
        'voice_layer': 88
    }
    return generate_yaml_report(scores)
    # Output: review-report.yaml with numerical grades
```

### ✅ Good: Auto-Research

```python
def write_article(topic, channel):
    # Just do it - don't ask "do you have materials?"
    sources = auto_search(topic)  # Search official blog, HN, Reddit, X
    draft = write_with_facts(topic, sources, author_voice)
    return draft  # Article with simple reference list appended
```

### ❌ Bad: Manual Material Submission

```python
def write_article(topic, channel):
    ask_user("Do you have materials?")
    materials = wait_for_user_upload()
    ask_user("Confirm material reception?")
    catalog_materials_with_claim_ids(materials)
    ask_user("Confirm content contract?")
    # ...5 more confirmation gates
```

### ✅ Good: Merged Review

```python
def write_and_review(topic):
    draft = write_with_realtime_fact_check(topic)  # Verify while writing
    suggestions = one_pass_review(draft)  # Single review, plain text
    return draft, suggestions
```

### ❌ Bad: Separate Review Layers

```python
def write_and_review(topic):
    draft = write(topic)
    evidence_report = evidence_layer_review(draft)
    editing_report = editing_layer_review(draft)
    voice_report = voice_layer_review(draft)
    return draft, [evidence_report, editing_report, voice_report]  # 3 YAML files
```

## File Naming

When creating new internal state files:

- ✅ `setup.md` — clear, friendly
- ✅ `research-notes.md` — describes what it contains
- ✅ `final-check.md` — action-oriented
- ❌ `capability-preflight.md` — sounds like airport security
- ❌ `acceptance-report.yaml` — sounds like quality inspection
- ❌ `claim-verification-manifest.yaml` — sounds like legal audit

## Anti-Patterns to Reject

### ❌ "Build evidence archive first"

**Current (wrong)**: Phase 0 requires all materials upfront → catalog → index → then start writing.

**Should be**: Write directly, gather sources along the way, attach reference list at end.

### ❌ "Confirm every substep"

**Current (wrong)**: Material confirmation → content contract confirmation → outline confirmation → draft confirmation → review confirmation → acceptance confirmation.

**Should be**: Only confirm at genuine decision forks (channel selection, publish action). Everything else: just do it, show progress.

### ❌ "Show the machinery"

**Current (wrong)**: Show users `claim_id: claim_001`, `source_sha256: abc123...`, `diagnostic_id: WM-CAP-001`.

**Should be**: These are internal quality mechanisms. Never expose implementation details as user-facing concepts.

### ❌ "More layers = better quality"

**Current (wrong)**: Separate evidence layer → editing layer → voice layer reviews, each with scores and YAML reports.

**Should be**: Verify facts WHILE writing (not after), then give ONE round of plain-text editing suggestions.

## Before Implementing Features

Ask yourself: **"Does this make the output feel more like an evidence审查报告, or more like something a real author would write?"**

If answer is "evidence report", stop and reconsider the approach.

**Key question**: "Would a tech blogger use this feature, or would they find it bureaucratic?"

## Required Reading Before Changes

1. `docs/PRODUCT_VISION.md` — what we're building and why
2. `skills/writing-master/DESIGN_PRINCIPLES.md` — detailed implementation rules
3. `CLAUDE.md` (repo root) — technical setup + product principles summary

## Quick Checklist

Before submitting changes that affect user experience:

- [ ] No compliance language in user-facing text (验收, 审计, 预检)
- [ ] No internal state fields shown to users (_sha256, _snapshot, _readiness)
- [ ] No YAML reports as user deliverables
- [ ] No unnecessary confirmation gates added
- [ ] File names are friendly (`setup.md`), not bureaucratic (`capability-preflight-v2.yaml`)
- [ ] Feature works for `evidence_level: balanced` by default
- [ ] Quick mode stays quick (< 10 min, < 5 files)

## Summary

**Goal**: Writing assistant that feels like a helpful editor, not a compliance department.

**Core principle**: Evidence tracking is infrastructure (keep it), not product surface (hide it).

**Test**: If a feature makes articles read more like audit reports than blog posts, it's moving in the wrong direction.
