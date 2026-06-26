# Decision Log — Import grilling, grill-me, resolving-merge-conflicts, improve-codebase-architecture

**Date:** 2026-06-26
**Area:** tooling / engineering process

## Context

The user pointed at https://github.com/mattpocock/skills/tree/main/skills/engineering and asked to set up "grill me, domain modelling and other necessary ones" in `.claude/skills/`. OptiMILES already had its own `domain-modeling`, `diagnosing-bugs`, `tdd`, `codebase-design`, `to-issues`, `to-prd` (adapted to this project's vocabulary, not generic copies), so the gap was specifically the "grill me" interview mechanic and a few process skills that don't yet exist here.

Surveyed the full mattpocock/skills repo (engineering, productivity, misc, deprecated folders) and presented the candidates not already covered: `grilling`/`grill-me` (the interview mechanic), `resolving-merge-conflicts`, `improve-codebase-architecture`, `prototype`, and `triage`.

## Decisions

1. **Added `grilling`** (`.claude/skills/grilling/SKILL.md`) — model-invocable skill implementing the one-question-at-a-time relentless interview with recommended answers, stopping when the design tree is resolved. Other skills can call into it instead of re-implementing Q&A loops.
2. **Added `grill-me`** (`.claude/skills/grill-me/SKILL.md`) — thin user-facing entry point that runs a `grilling` session, matching the upstream split between the engine and the trigger.
3. **Added `resolving-merge-conflicts`** (`.claude/skills/resolving-merge-conflicts/SKILL.md`) — ported near-verbatim; it's generic and safe as-is (always resolve, never `--abort`, never force-push without asking).
4. **Added `improve-codebase-architecture`** (`.claude/skills/improve-codebase-architecture/SKILL.md` + `HTML-REPORT.md`) — adapted from upstream to use OptiMILES's actual module boundary (the five backend engines, per `codebase-design`) instead of a generic `CONTEXT.md`/ADR vocabulary, and to reference `docs/decisions/` instead of an ADR folder that doesn't exist in this repo. Scoped explicitly to be a refactor-review tool for once `backend/` has real code — not a Phase 0 scaffolding tool.
5. **Updated root `CLAUDE.md`'s "Skills & Agents — When To Use Them"** table with trigger entries for all four new skills, per the rule (added in the prior session) that this table is the durable mechanism making skills actually get recalled and used, and must stay in sync with `.claude/skills/*`.

## Not done (deferred)

- **`prototype`** — throwaway-prototype workflow (logic vs. UI variant prototyping). Not requested by the user in the follow-up selection; can be added later if disposable-prototype work becomes a recurring need.
- **`triage`** — GitHub issue/PR triage state machine. Skipped: OptiMILES is Phase 0 (pre-issue-tracker, per CLAUDE.md's Current Development Phase), so there's no live issue queue for it to operate on yet. Revisit once `to-issues` output actually accumulates a backlog worth triaging.
- **`ask-matt`, `setup-matt-pocock-skills`** and other personal/author-specific upstream skills — not applicable to this project, excluded as out of scope rather than evaluated.
