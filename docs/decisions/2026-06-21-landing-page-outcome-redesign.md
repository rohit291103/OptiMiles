# Decision Log — Landing Page Outcome-First Redesign

**Date:** 2026-06-21
**Area:** Frontend

---

## Context

The landing page (rebuilt during the [frontend MVP cleanup](2026-06-21-frontend-mvp-cleanup.md)) had the right premium dark/gold aesthetic but read like an engineering doc, not a product landing page. It led with internal engines (Reward Knowledge Engine, Optimization Engine, Simulation Engine) — implementation details — instead of the outcomes users actually want (business-class travel, luxury stays, lounge access). The user supplied a detailed redesign brief asking for an outcome-first structure, richer storytelling, and premium motion, while explicitly preserving the existing brand, palette, typography, and dark aesthetic.

Two parts of the brief conflicted with established project rules, so both were resolved with the user before any code was written.

## Decisions

1. **Brand names stay generic.** The brief leaned on named partners (Singapore Airlines, KrisFlyer, Marriott Bonvoy, Accor ALL). The [frontend MVP cleanup](2026-06-21-frontend-mvp-cleanup.md) had deliberately stripped all such names from the UI project-wide. User confirmed: keep copy generic ("business class," "frequent-flyer transfer," "luxury hotel stay," "hotel loyalty programs"). The earlier cleanup decision stands; this redesign does not reintroduce partner names. Verified clean via repo-wide grep.

2. **Dependency-free, CSS-only animation — no Framer Motion.** The brief asked for Framer Motion and real destination/card photography. The project is intentionally dependency-free (CSS animations, in-repo carousel/tabs/accordion primitives, zero animation libraries) per root `CLAUDE.md`'s "avoid unnecessary framework complexity." User confirmed CSS-only. All motion is done with CSS keyframes + `IntersectionObserver`; imagery uses styled gradient placeholders ready to swap for real PNGs later. No new npm dependencies were added.

3. **Page restructured outcome-first.** `page.tsx` now flows: Hero → Dream Outcomes → How It Works → Why Trust → Goal Simulator → Example Strategy Output → Cards You Carry → Ecosystem wall → Built For → Capabilities (engines, demoted) → Why OptiMiles Exists → FAQ → Final CTA. Engine/architecture content is moved below the outcome sections rather than leading. Goal-oriented CTA copy throughout ("Build my reward strategy"). Hero copy changed to "Turn everyday spending into extraordinary travel experiences."

4. **New section + primitive components added.** Sections: `dream-outcomes`, `how-it-works` (4-step timeline w/ progress connector), `trust-pillars`, `strategy-output` (realistic recommendation card), `ecosystem-marquee`, `built-for`. Reusable animation primitives: `Reveal` (scroll-reveal via IntersectionObserver) and `CountUp` (rAF count-up animation). Both honor `prefers-reduced-motion`.

5. **Simulator, cards carousel, and FAQ rebuilt.** Goal simulator gained timeline, preferred-airline, and multi-select current-cards inputs plus count-up animated results. Supported-cards carousel got 4s autoplay, pause-on-hover, drag/touch, and active-card scaling (self-contained, still no embla/swiper). FAQ expanded to the brief's 7 questions, kept generic.

6. **New CSS utilities/keyframes.** Added `bg-hero-field` (slow-drifting gradient), `bg-starfield`, `.reveal` (scroll-reveal), and `hero-drift`/`starfield-drift` keyframes in `globals.css`, all gated behind a `prefers-reduced-motion` block.

Verified: `npm run build` and `npx eslint src` both clean; live dev-server render returned HTTP 200 with all sections present and no compile errors.

## Not done (deferred)

- **Real photography.** No destination/card images were fabricated or downloaded — gradient placeholders stand in until the user supplies PNGs into `/public`.
- **Testimonials + stats bar.** The previous homepage's stats bar and testimonials section are not in the new brief's structure and were dropped from `page.tsx`. `testimonials.tsx` remains in the repo unused rather than deleted.
- **Browser eyeball pass.** Build/lint/HTTP-200 verified, but a human visual scroll-through of the animations and gradient placeholders has not been done.
