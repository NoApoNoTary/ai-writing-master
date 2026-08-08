# Claude project memory

## Product Principles — READ THIS FIRST

**Core Goal**: Build an AI writing assistant that produces articles feeling like the author wrote them, not like AI wrote them. Primary scenario: hot-topic speed writing (15-20 min from topic to publishable draft).

### Critical Boundary: Internal vs User-Facing

**Evidence tracking (`sources.yaml`, `claims.yaml`), multi-layer review, and version control are internal quality mechanisms. They must NOT leak into user-visible outputs.**

✅ **Keep internal**:
- Fact traceability, automatic verification, SHA-256 hashing
- `runs/{task_id}/` state files, snapshots, version control

❌ **Hide from users**:
- `claim_id`, `source_sha256`, `capability-preflight.md`, diagnostic codes
- YAML review reports as deliverables
- Compliance language: "验收" (acceptance), "审计" (audit), "预检" (preflight)
- Internal state: `persona_snapshot`, `voice_snapshot_sha256`, `handoff_runtime`

**Users see**: "Article ready! Optional editing suggestions..." (plain text)  
**Users don't see**: Review scores, claim verification tables, diagnostic codes

### Evidence Level Defaults

- Quick: `relaxed` — prevent fabrication, prioritize speed
- **Standard: `balanced`** — verify core data, allow opinions (DEFAULT for hot-topics)
- Deep: `strict` — full source tracking (serious reports only)

**Don't apply `strict` to hot-topic articles.** Personal experiences and opinions can be written directly.

### Key Rules

1. **Default to automation** — only ask when genuinely needed. Don't confirm every step.
2. **Show progress, hide implementation** — "Collecting info (2/5)", NOT "capability-preflight: ready"
3. **Deliver finished articles** — not intermediate YAMLs. Quick mode = 1 markdown, not 7 files.
4. **Give suggestions, not scores** — plain text, NOT YAML reports with numerical grades
5. **Use creative language** — "准备, 撰写, 打磨, 定稿". AVOID: "验收, 审计, 预检, 批准"

**Before adding features, ask**: "Does this make output feel more like evidence审查报告, or like something a real author wrote?" If evidence report, rethink.

Read `docs/PRODUCT_VISION.md` and `skills/writing-master/DESIGN_PRINCIPLES.md` for details.

## Technical Guidelines

- Canonical repo: `/home/amose/ai-writing-master`; do not copy runtime state.
- Layout: application code under `src/writing_master/`, tests under `tests/`, skills under `skills/`, docs under `docs/`.
- If `.codegraph/` exists, use CodeGraph first (`codegraph explore "..."`) before grep/find.
- Shared runtime is `~/.writing-master`; resume with an explicit `task_id`/`run_dir`, and never have two writers modify the same run.
- Validation: `PYTHONPATH=src python -m unittest discover -s tests -v`; `PYTHONPYCACHEPREFIX=/tmp/awm-pyc python -m compileall -q src tests`; `bash -n install.sh`; `./bin/writing-master --help`.

### ⚠️ Workflow Tool Usage — CRITICAL

**When writing Workflow scripts that spawn subagents:**

- ❌ **NEVER instruct subagents to use the Read tool** — it's currently broken and causes infinite permission loops
- ✅ **Always use `Bash` with `cat` to read files**: `cat /path/to/file.py`
- ✅ **Use `grep`/`find` for searching**: `grep -r "pattern" /path --include="*.py"`
- ✅ **Use `Edit` tool for modifications**: works correctly

**Example workflow prompt pattern:**
```javascript
await agent(
  `CRITICAL: Use Bash with cat to read files. Do NOT use the Read tool - it's broken.
  
  Use: cat /path/to/file.py
  Then: analyze and return findings`,
  { label: 'Task name' }
)
```

Without this explicit instruction, subagents default to Read and get stuck in permission loops.
