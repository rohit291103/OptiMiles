# Architecture — Multi-tool AI Agent/Skill Setup (v1)

**Status:** Current implementation across `.claude/`, `.cursor/`, `.github/`.

---

## Why this exists

OptiMILES is built using multiple AI tools (Claude Code, Cursor, GitHub Copilot), and root `CLAUDE.md`'s AI Collaboration Model already assumes work crosses between AI tools. Whoever opens the repo in any of these three tools should get equivalent guidance, not guidance that depends on which tool they happen to have open.

## Pattern: one canonical source, thin pointers elsewhere

Each tool has a different mechanism for "package up a reusable instruction set" and none of them overlap exactly:

| Tool | Mechanism | Trigger | Closest to a... |
|---|---|---|---|
| Claude Code | `.claude/skills/<name>/SKILL.md` | model decides from `description`, or user runs `/<name>` | both model- and user-invoked skill |
| Claude Code | `.claude/agents/<name>.md` | delegated subagent call | a reviewer/specialist subagent |
| Cursor | `.cursor/rules/<name>.mdc` | `alwaysApply`, `globs` (path-based), agent-requested (description-based), or manual `@<name>` | a skill, depending on frontmatter |
| GitHub Copilot / VS Code | `.github/prompts/<name>.prompt.md` | manual `/<name>` in chat | a user-invoked skill |
| GitHub Copilot / VS Code | `.github/instructions/<name>.instructions.md` | `applyTo` glob, auto-applied by file path | a path-scoped rule |
| GitHub Copilot / VS Code | `.github/agents/<name>.agent.md` | delegated subagent call | a reviewer/specialist subagent |

Cursor has no skill or subagent concept of its own — only Rules. Writing the same detailed prose three times per topic would drift (this is the exact failure mode `docs-sync` already exists to catch for `/docs`). So:

- **`.claude/` is canonical.** Full skill/agent content lives there.
- **`.cursor/rules/*.mdc`** and **`.github/{prompts,instructions,agents}/*`** are short files: correct frontmatter for that tool's trigger mechanism, a few bullets of the core rule, and an explicit pointer to the canonical `.claude/...` file (the same pattern `frontend/CLAUDE.md` already uses — it's just `@AGENTS.md`).
- The one exception is `.cursor/rules/optimiles-constitution.mdc` (`alwaysApply: true`), which inlines enough of root `CLAUDE.md` to be useful standalone, since Cursor won't proactively open the root constitution on its own.

## Current inventory

**Dev**
- `diagnosing-bugs` — debugging loop, reward-math bugs treated as highest severity
- `codebase-design` — module-boundary checklist (the five backend engines), blocks premature abstractions
- `backend-reviewer` (agent) — read-only review enforcing "LLMs never calculate rewards directly," module boundaries, no premature infra

**Testing**
- `tdd` — test-first workflow, mandatory for the four deterministic engines

**Planning**
- `to-issues` — PRD/decision → vertical-slice checklist
- `handoff` — compress context into a structured note for ChatGPT/Gemini/teammates (`docs/prompts/template.md` shape)

**Product management**
- `domain-modeling` — keeps reward/finance vocabulary consistent (transfer ratio vs. valuation, accrual vs. redemption, milestone vs. cap, etc.)
- `to-prd` — conversation → PRD draft in `docs/prd/`

**Frontend (pre-existing, unchanged this pass)**
- `docs-sync` (skill) — keeps `/docs` structured and de-duplicated
- `frontend-reviewer` (agent) — real-browser frontend QA

Deliberately not built (from the [mattpocock/skills](https://github.com/mattpocock/skills) reference list this set was scoped against): `triage`, `grill-me`, `teach`, `improve-codebase-architecture`, `prototype`, `git-guardrails`, and tooling specific to his own setup (issue-tracker terminology, a type-assertion migration tool). Revisit `improve-codebase-architecture` and `git-guardrails` once `backend/` has real code and this repo has a git history worth guarding.

## Adding the next one

1. Write the full version in `.claude/skills/<name>/SKILL.md` (or `.claude/agents/<name>.md` if it's a reviewer/specialist).
2. Add a thin pointer in `.cursor/rules/<name>.mdc` with frontmatter matching how it should trigger (always/path/agent-requested/manual).
3. Add the Copilot equivalent: `.github/prompts/<name>.prompt.md` for anything user-invoked, `.github/instructions/<name>.instructions.md` for anything path-scoped, `.github/agents/<name>.agent.md` for a reviewer/specialist.
4. Add one line to the inventory table above. Don't let this doc and the actual files drift — it's describing what exists, not aspirational.
