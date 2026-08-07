# AI Writing documentation index

`README.md` is the project overview. This file routes documentation so a
normal task does not load every plan and research note.

## Read by task

| Task | Start here | Then read |
|---|---|---|
| New user / first article | `docs/quick-start.md` | channel-specific contract only if named |
| **Implementing new features** | **`docs/PRODUCT_VISION.md`** | **`skills/writing-master/DESIGN_PRINCIPLES.md` and `AGENT.md`** |
| CLI or automation | `docs/cli-guide.md` | the command implementation and targeted tests |
| Repository state / migration | `PROJECT_SUMMARY.md` | relevant `docs/2026-*-architecture-review.md` |
| Product or channel contract | `docs/proposals/` | the named PRD and acceptance tests |
| Current engineering plan | `docs/plans/` | only the active plan; older plans are history |
| Goal or handoff recovery | `docs/goals/` | the exact `task_id`/run directory named by the task |
| Research background | `docs/research/` | only the cited source or brief |
| Skills and workflow behavior | `skills/` | the selected skill's `SKILL.md` and references |

## Canonical ownership

- **Product vision and principles**: `docs/PRODUCT_VISION.md` — what we're building and why.
- **Design principles**: `skills/writing-master/DESIGN_PRINCIPLES.md` — implementation rules to prevent drift toward "证据审查系统".
- **Agent instructions**: `skills/writing-master/AGENT.md` — guidelines for AI agents working on this skill.
- User-facing onboarding: `docs/quick-start.md`.
- CLI contract: `docs/cli-guide.md` and the CLI implementation.
- Current product/engineering truth: the active contract and code/tests.
- Historical decisions: dated goals, plans, proposals and changelog entries.
- Runtime state: `~/.writing-master/`; never treat it as repository docs.

**Critical**: Before implementing new features, read `docs/PRODUCT_VISION.md` to understand the boundary between internal quality mechanisms (evidence tracking, multi-layer review) and user-facing experience (streamlined creative flow). These mechanisms must NOT leak into user-visible outputs.

Do not merge dated plans into README or `CLAUDE.md`. Update the authoritative
document in place when a current contract changes, and leave history dated.
