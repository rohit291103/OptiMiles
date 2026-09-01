# Decision Log — Mobile-first pass (Phase 1)

**Date:** 2026-09-01
**Area:** frontend / design system
**Roadmap:** `docs/prd/product-roadmap-v1.md` → Phase 1, "Mobile-first pass on the existing surfaces"

## Context

User testing said *"it should be an app"*, and the roadmap's reading of that is partly a form-factor request and partly a usability one: the goal wizard and dashboard were built desktop-first, and most people reach them on a phone browser long before any app exists. This is also the stated prerequisite for Phase 4.

## Approach — measure, then fix

The roadmap describes the problem as "138 breakpoint usages across 58 components but wide-viewport layouts". Rather than trusting that framing, the surfaces were audited in a real headless browser at **375×667 (iPhone SE — the realistic floor)** and **390×844**, with a script measuring three things per route: page-level horizontal overflow, computed font sizes under 12px, and interactive elements under 44×44 (Apple HIG).

**The framing turned out to be wrong in a useful way.** There was **no horizontal overflow anywhere** — the earlier per-feature work had already handled layout. What the audit found instead was systematic and invisible to a layout review:

| Defect | Worst instances |
|---|---|
| Tap targets under 44×44 | Goal wizard **"Continue" at 98×30** (the primary CTA of the main flow); nav **hamburger at 36×36** (the only route to navigation on a phone); card-picker chips 38px; programme chips 38px; **footer links 18px tall** |
| Text under 12px | 11px stat-tile labels and section headings across the app; a 10.4px card tier label |

A 30px-tall primary CTA and an 18px-tall link are not layout bugs — a screenshot looks fine. They are only visible when you measure.

## Decisions

1. **Fix at the design-system level, not the call site.** The wizard's Continue was short because the shared `Button` defaults to `h-8` (32px). Patching that one button would have left every other button in the app the same size. `Button`, `TabsTrigger`, `Brand` and both pickers were changed instead — one edit each, correct everywhere.

2. **Raise the mobile breakpoint only; leave desktop untouched.** Every change is `h-12 sm:h-8` / `min-h-11 sm:min-h-0` / `text-xs sm:text-[11px]`. The desktop proportions have been reviewed and approved repeatedly; this pass is about thumbs, and a phone-sized floor should not push the desktop design around. It also keeps the diff reviewable — every line says what it does at which width.

3. **44px is the floor, and `h-11` was not enough.** `h-11` measured 42px in practice on the wizard CTA, so `Button` uses `h-12` (48px) on phones with real margin rather than sitting exactly on the line.

4. **12px is the text floor on phones.** The design's 10–11px uppercase labels are legible on a laptop and not on a phone; they now render at 12px below `sm:` and are unchanged above it.

5. **The audit script is the artifact, not the fix list.** It lives in the scratchpad rather than the repo (it needs a running dev server and Playwright), but the measurements it takes — overflow, sub-12px text, sub-44px targets — are the checks worth re-running whenever a surface changes, and are worth folding into the `frontend-reviewer` agent's routine.

## What shipped

- `ui/button.tsx` — `default`/`lg` → `h-12` on phones, `sm` → `h-9`, icon variants → `size-11`
- `ui/tabs.tsx` — `TabsTrigger` `min-h-11` (homepage feature tabs, strategy route tabs)
- `site-nav.tsx` — hamburger `size-9` → `size-11`
- `brand.tsx` — the wordmark is a link home; `min-h-11` on phones
- `site-footer.tsx` — text links become padded 44px rows on phones (tighter `space-y` to compensate); social icons `size-11`
- `ui/card-picker.tsx`, `ui/program-chooser.tsx` — chips `min-h-11`
- `app/portfolio-view.tsx`, `best-card.tsx` — "Edit wallet", "Clear my wallet", "Remove it", "Save these as my cards"
- Seven files' sub-12px labels raised at the mobile breakpoint

## Result

Re-audited at both viewports across the homepage (goal wizard), Best Card and Portfolio View:

- **0** page-level horizontal overflow
- **0** text under 12px
- **0** tap targets under 44px, with one over-strict flag remaining: a footer text link measuring 42px *wide* and 44px *tall*. Width is not the constraint for an inline link in a stacked list.
- **0** console errors

`tsc`, `eslint` and `next build` clean; backend suite unaffected at **500 passed**.

## Not done, deliberately

- **The homepage is ~16,000px tall on a 375px screen** (roughly 24 screens of scrolling). That is a marketing-page content decision, not a mobile defect, and shortening it is a separate piece of work with its own trade-offs.
- **Signed-in routes (`/goals`, `/goals/[id]`) were not driven live** — they sit behind Google OAuth. Their controls inherit the same `Button`, `TabsTrigger` and text-size fixes, so the systematic defects are addressed, but a click-through behind login is still worth doing.
