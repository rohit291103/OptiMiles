# Decision Log — Frontend MVP Cleanup

**Date:** 2026-06-21
**Area:** Frontend, root documentation, Claude Code project infra

---

## Context

The landing page (`frontend/src/app/page.tsx`) was built ahead of the root `CLAUDE.md` instructions being followed consistently — the constitution doc had become duplicated, the dark UI had no `color-scheme` set (native scrollbar/select/input controls rendered in the browser's light theme against the dark site), and the card list showed only the 6 MVP-active cards with no signal that more cards are coming.

## Decisions

1. **Root `CLAUDE.md` deduplicated.** The entire document had been pasted twice end-to-end (921 lines → 461 lines after removing the exact duplicate). No content was changed, only the duplication removed.

2. **Dark-theme native UI fixed.** Added `color-scheme: dark` plus a themed scrollbar (`globals.css`) so the browser's native scrollbar, the destination `<select>`, and number-input spinners render in dark mode instead of clashing OS-light-theme controls. This was the most likely cause of the reported "scrolling issues / not clean" feedback — no horizontal overflow or console errors were found in testing.

3. **Card roster expanded with Active / Coming soon status.** `page.tsx` now shows the full 18-card roadmap from `docs/prd/mvp_scope_1.md`, grouped by tier (Premium Travel, Mid-Tier Reward, Airline/Travel Specific), with the 6 cards from CLAUDE.md's "Initial Supported Cards" marked **Active** and the rest **Coming soon**. This keeps the UI honest about what the optimizer actually supports today while showing the roadmap.

4. **Claude Code project infra started.** Per user request: a `docs-sync` skill (`.claude/skills/docs-sync/`) to keep `/docs` aligned with the Documentation Rules in CLAUDE.md, and a `frontend-reviewer` subagent (`.claude/agents/frontend-reviewer.md`) to catch design-system and overflow/scroll regressions on future frontend changes. A reward-data-curator agent was explicitly deferred until the backend/data layer exists.

## Not done (deferred)

- Backend scaffolding — `backend/` is still empty; out of scope until Phase 0 architecture work begins per CLAUDE.md's "Current Development Phase."
- Reward data curator agent — deferred until there's actual card/reward data to curate.
