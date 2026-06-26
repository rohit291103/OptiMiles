# Decision Log — Landing Page Product-First, Full-Bleed Restructure

**Date:** 2026-06-26
**Area:** Frontend
**Branch:** `redesign/full-bleed-simulator-hero`

---

## Context

The user shared three reference sites — Apple Intelligence, Replit, and ventriloc.ca — with two distinct asks:

1. **Replit pattern:** the thing you sell sits at the very top and is immediately usable. "For our simulator / when we build backend, the top should be the place where the user can directly use the app, then below, as we scroll, we show more info." Replit lands you on a usable prompt box; marketing comes after.
2. **Apple / Ventriloc pattern:** use the *entire* viewport width — full-bleed, generous space, progressive reveal — instead of a narrow centered column.

The prior [outcome-first redesign](2026-06-21-landing-page-outcome-redesign.md) had the Goal Simulator buried as roughly the 5th section (`#simulate`), and every section was locked to a centered `max-w-6xl` column.

## Decisions (confirmed with the user before building)

1. **Hero approach — headline hero, simulator directly below.** Keep a strong full-viewport headline as section 1, but pull the live Goal Simulator up to **section 2** (visible on first scroll), not buried mid-page. (User chose this over "simulator *is* the hero" and over a side-by-side split hero.)

2. **Spatial system — full-bleed sections.** Break out of the centered `max-w-6xl` cage. Key sections (hero, simulator, strategy output, supported cards, feature tabs) now span the viewport with a wider `max-w-375` content measure and asymmetric framing. Text-led sections keep the narrower readable measure.

3. **Build now, on a new branch.** All work landed on `redesign/full-bleed-simulator-hero` (not `main`).

## Implementation

- **New primitive:** `components/sections/section-shell.tsx` exports `Bleed` (owns full viewport width, optional `banded` tint + hairline border for alternating rhythm, optional `id` with `scroll-mt-24`) and `Inner` (re-constrains content; `wide` → `max-w-375`, default → `max-w-6xl`). `page.tsx` sections were migrated onto these.
- **Simulator promoted** to the first section below the hero: full-bleed, banded, split layout with a sticky left heading column ("Pick your cards. / See the path.") beside the live simulator card. Internal simulator header simplified (dropped the redundant "Card strategy simulator" eyebrow now that the section owns the heading).
- **Hero** widened to `max-w-375`; scroll cue + secondary CTA repointed from `#how` to `#simulate` ("Try it now" / "Try the simulator") so the product reads as immediately below.
- **Nav** reordered so **Simulator** leads, and widened to match `max-w-375`.

## Verification

`tsc --noEmit` clean, `eslint` clean, dev server returns HTTP 200, rendered section order confirmed as `simulate → how → cards → features → faq`. The only console error in the dev log originates from the React DevTools browser extension, not project code.

## Amendment — edge-to-edge + cinematic (same session)

The first pass kept a wide-but-contained `max-w-375` (1500px) measure. The user pushed back: on a wide monitor that still read as "a box in blank margins," and the scroll felt "very simple." Re-confirmed direction: **true edge-to-edge** (no content cage) + **cinematic pinned scroll** like the Apple Intelligence page, full redesign in one pass.

Changes:
- **Removed the content cage.** `Inner` is now the only horizontal gutter — a small fluid pad (`px-5 sm:px-8 lg:px-12 xl:px-16 2xl:px-24`). No `max-w` on section wrappers. Nav and footer adopt the same gutter. Verified in served HTML: 0 `max-w-375` wrappers, 15 edge-to-edge gutters. Readable line-length for long copy is restored locally with `max-w-prose` / the new `Measure` helper, not by re-centering sections.
- **Pinned scroll.** `Hero` is a pin-and-release stage (scale/blur/fade via `useScroll`/`useTransform`). New `simulator-scene.tsx` is an Apple-style pinned scene: ~260vh track, `sticky top-0 h-screen` stage, intro copy holds while the live simulator scales + fades up, then both pin so the visitor can use it before release. A reusable `PinnedScene` primitive was added to `section-shell.tsx`. All effects collapse to static under `prefers-reduced-motion`.
- **Fluid display type.** Headlines use `clamp()` so they scale with the now-full-width canvas (hero `clamp(3rem,8.5vw,8rem)`).
- `trust-pillars` bumped to a 4-up grid at `xl` so it fills the width instead of stretching 2 cards.

Verified: `tsc` clean, `eslint` clean, dev server HTTP 200, section order intact (`simulate → how → cards → features → faq`), pinned track present in served HTML.

## Amendment 2 — pinned-simulator reverted, decorative frame removed (same session)

User feedback after the cinematic pass surfaced two issues, both fixed:
- **Simulator pin reverted.** The ~260vh pinned simulator scene hijacked the scroll wheel and clipped the simulator's expanding results ("sticks in between, looks very bad"). A pinned scroll scene is wrong for an *interactive* form. `simulator-scene.tsx` is now a normal freely-scrollable block with a one-time `whileInView` scale/fade entrance + sticky intro copy. The unused `PinnedScene` primitive was removed from `section-shell.tsx`. The hero keeps its pin-and-release (it's passive).
- **`PageFrame` removed.** Its fixed side-rails with gold dots travelling down them ("droplets dropping in motion") were built for the old centered column; in the edge-to-edge layout they sat inside the content. Component deleted (`page-frame.tsx`). The `bg-starfield` drift animation was also removed (now a static texture) for the same "distracting edge motion" reason.

## Notes / follow-ups

- The simulator remains a **static mock** (hardcoded destinations/mile counts) — unchanged by this work. The "product at the top" pattern is now in place structurally, ready for the real Simulation Engine once the backend exists.
- Drift observed (out of scope here): the [2026-06-21 redesign](2026-06-21-landing-page-outcome-redesign.md) recorded the project as "dependency-free, no Framer Motion," but `hero.tsx`/`hero-flow.tsx` now import `motion/react`. Flagging for a future reconciliation of that decision, not changed in this task.
