# Agent Instructions for Writing Master

**Purpose**: Guidelines for AI agents (Claude, GPT, etc.) working on this skill to stay focused on delivering value to readers.

## Core Product Identity

You are implementing a **writing system that delivers value to readers**, not an evidence auditing system or "human-like writing" simulator.

**Target experience**: User says "write an article about Claude 5 launch for WeChat" → System auto-researches → Writes to provide value → User reviews → Publishes. Total time: 15-20 minutes.

## Critical Rule: Value First, Everything Else Serves It

**为读者提供价值是唯一目的。** Everything else—evidence tracking, writing quality, author voice—exists to serve this goal.

### What is "Value"?

Value is **multi-dimensional and open-ended**. Examples include (but are not limited to):
- **Information value**: Quickly understand hot topics, tech trends, product updates
- **Decision value**: Help readers judge "Is this worth my attention?" "Should I follow this trend?"
- **Emotional value**: Resonance, inspiration, "I'm not the only one thinking this way"
- **Social value**: Worth sharing to friends/groups, demonstrates reader's insight
- **Time value**: Get a quality article in 15-20 minutes instead of hours
- **Any other value you identify that readers need**

**Do NOT limit yourself to these categories.** If you identify other ways to provide value, pursue them.

### Quality Metrics

**The ONLY measure of quality**:
- ✅ Readers want to keep reading (not close after scanning)
- ✅ Readers feel they gained something (not wasted time)
- ✅ Readers want to share it (not forget after reading)
- ✅ Readers come back (not unsubscribe)

**"Human-like" is just a quality baseline**: Don't write "AI-flavored nonsense"—empty, repetitive, no viewpoint, feels assembled. But mimicking humans is NOT the goal; providing value IS.

## Internal Mechanisms vs User Experience

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

**But evidence tracking is still important**—it's how we ensure accuracy (information value). Just keep it internal.

## Implementation Patterns

### ✅ Good: Value-Focused Review

```python
def review_article(draft, reader_context):
    """Ask: Does this provide value to readers?"""
    issues = []
    
    # Information value: Is this accurate?
    if has_factual_errors(draft):
        issues.append("Paragraph 3: 'performance improvement 40%' - official blog says '35-45%', be more precise")
    
    # Readability value: Will readers keep reading?
    if paragraph_too_long(draft, 5):
        issues.append("Paragraph 5: quite dense, consider splitting")
    
    # Decision value: Does this help readers judge?
    if missing_practical_context(draft):
        issues.append("Add: what does this mean for typical users?")
    
    return format_as_suggestions(issues)
    # Output: Plain text suggestions that help provide more value
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
    # Problem: Scores don't tell us if readers will find value
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

- [ ] **Value-focused**: Does this help provide more value to readers?
- [ ] **Not just "human-like"**: Avoid confusing "mimicking humans" with "providing value"
- [ ] No compliance language in user-facing text (验收, 审计, 预检)
- [ ] No internal state fields shown to users (_sha256, _snapshot, _readiness)
- [ ] No YAML reports as user deliverables
- [ ] No unnecessary confirmation gates added
- [ ] File names are friendly (`setup.md`), not bureaucratic (`capability-preflight-v2.yaml`)
- [ ] Feature works for `evidence_level: balanced` by default
- [ ] Quick mode stays quick (< 10 min, < 5 files)

## Summary

**Goal**: A writing system that delivers value to readers.

**Core principle**: 
- **为读者提供价值是唯一目的。** Value is multi-dimensional and open-ended—discover what readers need.
- Evidence tracking is infrastructure (keep it internal), not product surface (hide it).
- "Human-like" is a quality baseline (avoid AI nonsense), not the goal itself.

**Test**: 
- If a feature makes articles read more like audit reports than blog posts, it's wrong.
- If an article doesn't provide value to readers, being "human-like" doesn't save it.
- Always ask: **Does this help readers?** Not: "Does this look like a human wrote it?"
