# Decision Log — Multi-tool Agent/Skill Expansion

**Date:** 2026-06-21
**Area:** Claude Code / Cursor / Copilot project infra, root documentation

---

## Context

The user asked for a curated set of dev/testing/planning/product-management skills and agents, pointing at [mattpocock/skills](https://github.com/mattpocock/skills) as inspiration, and asked for equivalent setups across `.claude`, `.cursor`, and `.copilot` so the guidance doesn't depend on which AI tool a contributor has open. While auditing `.github/copilot-instructions.md` to fold it into this pass, found it had the same whole-document duplication bug root `CLAUDE.md` had before its 2026-06-21 cleanup.

## Decisions

1. **`.github/copilot-instructions.md` deduplicated.** 920 lines → 460, matching root `CLAUDE.md`'s already-fixed content exactly (the two files are meant to be the same constitution). No content changed beyond removing the duplicate.

2. **Curated 7 skills + 1 agent for Claude Code**, scoped to dev/testing/planning/PM and to what's actually useful at Phase 0 (no backend code yet): `domain-modeling`, `to-prd`, `to-issues`, `handoff` (planning/PM — none of these need code to exist yet), `diagnosing-bugs`, `tdd`, `codebase-design` (dev/testing — written now so they're ready the moment `backend/` gets real code), and a `backend-reviewer` agent (sibling to the existing `frontend-reviewer`, enforcing the Engineering Philosophy's hard rule that LLMs never calculate reward values directly).

3. **Deliberately not ported:** `triage`, `grill-me`, `teach`, `improve-codebase-architecture`, `prototype`, `git-guardrails`, and anything specific to mattpocock's own tooling preferences (issue-tracker terminology, a type-assertion library). Either premature for a repo with no backend/tests/CI yet, or specific to a different author's workflow.

4. **Mirrored into Cursor and Copilot via thin pointers, not duplicated prose.** `.claude/` is the canonical source for every skill/agent's full content. `.cursor/rules/*.mdc` (10 files) and `.github/{prompts,instructions,agents}/*` (11 files) each get correct frontmatter for that tool's trigger mechanism plus a short summary and an explicit pointer back to the canonical `.claude/...` file — full rationale in `docs/architecture/ai-tooling-setup-v1.md`. The one exception is `.cursor/rules/optimiles-constitution.mdc` (`alwaysApply: true`), which inlines the constitution's load-bearing rules since Cursor won't proactively open root `CLAUDE.md` on its own.

## Not done (deferred)

- `improve-codebase-architecture` and `git-guardrails` skills — deferred until `backend/` has real code and a git history worth auditing/guarding.
- Wiring `to-issues` to actually create GitHub issues — no git remote exists yet; it outputs a checklist doc instead.
