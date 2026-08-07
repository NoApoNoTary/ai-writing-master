# Writing Master Design Principles

**Purpose**: Keep the system focused on delivering value to readers. Read this before implementing any new feature.

## Core Question

**"Does this help provide more value to readers?"**

If answer is no, or if it makes output feel more like an evidence report, stop and rethink.

## The Product We're Building

**Goal**: A writing system that delivers value to readers.

**Value is multi-dimensional and open-ended**, including but not limited to:
- Information value (understand hot topics quickly)
- Decision value (help readers judge "is this worth my attention?")
- Emotional value (resonance, inspiration)
- Social value (worth sharing)
- Time value (15-20 min to high-quality article)
- Any other value you identify that readers need

**Quality measurement**: Readers want to keep reading, feel they gained something, want to share it, come back for more.

**Primary Scenario**: Hot-topic writing
- User: "Write about Claude 5 launch for WeChat"
- System: Auto-research → Write to provide value → Generate images
- User: Quick review → Publish
- Timeline: 15-20 minutes total

**NOT building**: Investigative journalism tools, academic paper generators, compliance document systems, or "human mimicry simulators".

## Design Principles

### 1. Value First, Everything Else Serves It

**Right**: 
- Evidence tracking ensures accuracy (information value)
- Author voice makes content relatable (emotional value)
- Clear structure helps readers follow (readability value)
- All mechanisms exist to serve reader value

**Wrong**:
- Pursuing "human-like writing" as goal itself
- Adding evidence tracking because "it's rigorous" without asking if it helps readers
- Optimizing for "looks authentic" instead of "provides value"

### 2. Evidence Tracking is Internal Infrastructure

**Right**: 
- System verifies facts while writing
- `sources.yaml` + `claims.yaml` exist in `runs/{task_id}/` for quality assurance
- When user asks "where's this data from", show source

**Wrong**:
- Every sentence has a `claim_id` visible to user
- Draft includes footnotes like `[claim_001: verified, confidence: high]`
- User sees "证据层审校报告" as part of deliverables

### 3. Use Creative Language, Not Compliance Language

| ❌ Compliance Language | ✅ Creative Language |
|----------------------|---------------------|
| 验收 (acceptance inspection) | 定稿 (finalize) |
| 审计 (audit) | 审稿 (review) |
| 预检 (preflight check) | 准备 (prepare) |
| 批准 (approval) | 确认 (confirm) |
| 合同 (contract) | 方案 (plan) |
| Auditor | Editor / Reviewer |
| capability-preflight.md | setup.md |
| acceptance-report.yaml | final-check.md |

**Why it matters**: Language shapes how users perceive the tool. "验收" makes it feel like submitting homework to a teacher; "定稿" makes it feel like finishing a creative work.

### 4. Three Evidence Levels, Not One-Size-Fits-All

```yaml
evidence_level: strict | balanced | relaxed
```

**strict** (deep mode, serious reports):
- Every key claim requires verified source
- Three-pass review with detailed reporting
- Full `claims.yaml` with confidence scores
- **Purpose**: Maximum information value for critical content

**balanced** (standard mode, hot-topics, DEFAULT):
- Core data verified automatically
- Opinions and personal experiences allowed without sourcing
- One-pass review focusing on accuracy and readability
- **Purpose**: Deliver value efficiently—accurate information, readable content, 15-20 min turnaround

**relaxed** (quick draft, internal discussion):
- Prevent obvious fabrication only
- No formal review process
- Speed prioritized over exhaustive verification

**Current Problem**: The skill currently applies `strict` behavior to all modes. Standard mode should default to `balanced`.

### 4. Quick Mode Should Actually Be Quick

**Current (Wrong)**:
- Generates 7+ files: `brief.md`, `sources.yaml`, `claims.yaml`, `asset-manifest.yaml`, `review-report.yaml`, `revision-report.yaml`, `acceptance-report.md`
- Multiple confirmation gates
- Timeline: ~30 minutes

**Target (Right)**:
- Generates 1 file: `draft.md`
- Internal notes: `research-notes.md` (not exposed to user)
- One round of optional suggestions
- Timeline: 5 minutes

### 5. Reviews Give Suggestions, Not Scores

**Current (Wrong)**:
```yaml
# review-report.yaml
evidence_layer:
  score: 85/100
  issues:
    - claim_001: 来源可达性待验证
    - claim_003: 时效性存疑
editing_layer:
  score: 90/100
  ...
```

**Target (Right)**:
```markdown
Article complete! Optional improvements:

- Paragraph 3: "性能提升 40%" — official blog says "35-45%", could be more precise
- Paragraph 5: Example could be more specific (current: "某创业公司"; suggestion: name the company)

Type "apply" to accept suggestions, or "skip" to proceed.
```

**Key difference**: Conversation, not report card.

### 6. Default to Automation, Confirm Only When Necessary

**Confirm (user must decide)**:
- First-time mode selection
- Channel selection (WeChat vs X vs 知乎)
- Publish action
- Style preference (first time)

**Don't confirm (just do it)**:
- Starting research
- Generating draft
- Creating images
- Formatting for channel
- Using author's previous preferences

**Current Problem**: Too many gates — "素材接收确认", "内容契约确认", "大纲确认", "验收确认". Cut 70% of these.

### 7. Personas Control Perspective, Not Just Style

**Current implementation**: Persona + Voice Preset both control "how to speak" (word choice, sentence structure).

**Should be**:
- **Voice Preset**: Surface expression (vocabulary, rhythm, sentence length)
- **Persona**: Deeper perspective (default viewpoint, stance on new tech, priority dimensions)

**Example**: Writing about "Claude 5 launch"

| Persona | First Question Asked | Tone |
|---------|---------------------|------|
| Developer | What changed in the API? | Practical, technical |
| Product Manager | What problems can this solve? | Use-case focused |
| Investor | What's the market impact? | Strategic, competitive |

Currently missing: `perspective` field in persona templates.

### 8. Internal Files Stay Internal

**User deliverable** (what user copies/publishes):
- `final.md` — the article
- `cover.png` — generated cover image
- `final-wechat.html` — formatted for WeChat (if requested)

**Internal state** (stays in `runs/{task_id}/`):
- `setup.md` — mode, channel, persona selection
- `research-notes.md` — facts gathered, with sources
- `sources.yaml` + `claims.yaml` — fact traceability
- `revision-history.md` — what changed and why
- `status.json` — task state machine

**Never show users**: `capability-preflight.md`, `persona_snapshot_sha256`, `source_change_sha256`, diagnostic codes like `WM-CAP-001`.

### 9. Auto-Research for Hot Topics

**Current (slow)**:
1. User: "Write about Claude 5"
2. System: "Do you have materials?"
3. User: Provides links or asks system to search
4. System: Extracts, logs, indexes
5. System: "Content contract confirmation?"
6. User: Confirms
7. System: Starts writing

**Target (fast)**:
1. User: "Write about Claude 5 for WeChat"
2. System: [Auto-searches official blog + HN + Reddit + X] → [Writes] → "Article ready!"
3. User: Reviews, tweaks, publishes

Add `research_mode: manual | assisted | auto`:
- `auto` (default for standard mode): System finds sources automatically
- `assisted`: System suggests sources, user confirms
- `manual`: User provides all materials

### 10. Merge Review Phases

**Current (separate phases)**:
- Phase 4: Initial draft
- Phase 5a: Evidence layer review
- Phase 5b: Editing layer review  
- Phase 5c: Voice layer review
- Phase 6: Revisions based on all reviews

**Target (merged)**:
- Phase 3: Write (with real-time fact checking built in)
- Phase 4: One-pass review → give editing suggestions (plain text, not YAML)
- Phase 5: Apply user-selected suggestions → finalize

**Why**: Real authors don't "audit evidence" after writing. They verify facts WHILE writing, then polish the prose once.

## Common Anti-Patterns

### ❌ "Build archive first, write later"

**Symptom**: Phase 0 requires all materials upfront, catalogs them, builds evidence index before writing begins.

**Problem**: This is how librarians work, not how writers work.

**Fix**: Write first, gather sources along the way, attach reference list at the end.

### ❌ "Every step needs approval"

**Symptom**: 5+ confirmation gates in a standard flow.

**Problem**: Users want results, not to micromanage every substep.

**Fix**: Only stop for genuinely fork-in-the-road decisions. Everything else: do it automatically, mention it in progress updates.

### ❌ "Show the machinery"

**Symptom**: User-facing output includes `claim_id`, hash values, `mode_readiness: ready`, `diagnostic_id: WM-CAP-001`.

**Problem**: These are implementation details. Like showing users database schemas in a web app.

**Fix**: Internal state stays internal. User sees: "Article ready", not "capability-preflight: passed, persona_snapshot: frozen, voice_profile_version: 2".

### ❌ "More steps = better quality"

**Symptom**: Adding more review layers, more confirmation gates, more intermediate reports to "ensure quality".

**Problem**: Bureaucracy ≠ quality. Real quality comes from fact-checking during writing + one good editing pass.

**Fix**: Merge phases, automate checks, give users ONE round of suggestions.

## Implementation Checklist

Before merging any PR that touches core writing flow, verify:

- [ ] Does NOT add user-visible compliance language (验收, 审计, 预检)
- [ ] Does NOT expose internal state fields to user (no `_sha256`, `_snapshot`, `_readiness`)
- [ ] Does NOT generate YAML reports as user deliverables
- [ ] Does NOT add confirmation gates without strong justification
- [ ] New file names are user-friendly (`setup.md`), not bureaucratic (`capability-preflight-v2.yaml`)
- [ ] Feature works for `evidence_level: balanced` by default, not just `strict`
- [ ] Quick mode stays quick (< 10 minutes, < 5 files generated)

## When In Doubt

1. Read `docs/PRODUCT_VISION.md`
2. Ask: "Would a tech blogger friend use this, or would they find it too bureaucratic?"
3. Favor: Automation > Confirmation, Suggestions > Scores, Creative language > Compliance language

**Remember**: We're building a writing assistant, not an evidence审查system. If it feels like the latter, something went wrong.
