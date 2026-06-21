# OptiMiles — Project Tracker

A living snapshot of where the project actually stands right now — not a changelog. This file is **overwritten in place** after any session that does real work in `backend/`, `frontend/`, or `docs/`; it should never grow into an endless history. For *why* a decision was made, see `docs/decisions/` — that log is permanent and never rewritten. This file is disposable and just reflects current truth.

Maintained by the `tracker-sync` skill (`.claude/skills/tracker-sync/SKILL.md`). Read this file before starting new work in any chat; refresh it before ending one.

---

**Last updated:** 2026-06-21 — Wallet trimmed to a 4-card example, SBI removed from UI, and canonical card scope (CLAUDE.md + PRD) reconciled.

## Snapshot

Phase 0 (Product Definition & Architecture, per root `CLAUDE.md`). Backend has no code yet — schema and engine work hasn't started. Frontend is now a full outcome-first marketing site (hero → dream outcomes → how-it-works → trust pillars → simulator → strategy output → cards → ecosystem → built-for → capabilities → mission → FAQ → CTA) on the existing dark/gold design system, plus front-end-only login/signup pages. The hero is now a two-column layout — copy left, an animated goal→path flow card right (no longer empty). All motion is CSS/IntersectionObserver — still zero animation/carousel dependencies. Docs and Claude Code project infra (skills, subagents) are actively being built out alongside the product itself.

---

## Backend

### Done
- Nothing built yet — `backend/` contains only a placeholder file.

### In progress
- Nothing active.

### Next up
- Reward Knowledge Engine scaffolding (card data, reward rules, transfer ratios) per `docs/architecture/db-schema-v1.md`.
- FastAPI project skeleton + Supabase/Postgres wiring.

---

## Frontend

### Done
- **Hero visual — goal→path flow** (`src/components/sections/hero-flow.tsx`): fills the previously-empty hero right side. Glass card with a soft gold glow showing the real product journey (Your goal → Your cards → Transfer path → Redemption) connected by a **gold line that draws itself in** (`.hero-flow-line` + `hero-flow-draw` keyframe), staggered `Reveal` per node, and a footer payoff (`CountUp` 92,000 projected miles + "High confidence"). Hero converted to a 2-col grid (`lg:grid-cols-[1.05fr_0.95fr]`) that stacks on mobile. Dependency-free; all motion gated on `prefers-reduced-motion`. Generic brand names only.
- **Outcome-first homepage redesign** (`src/app/page.tsx`): restructured to lead with outcomes, not engines. New flow: hero (drifting gradient + starfield + goal→path flow card) → Dream Outcomes → How It Works (4-step timeline) → Why Trust (4 pillars) → Goal Simulator → Example Strategy Output → Cards You Carry → Ecosystem marquee → Built For → Capabilities (engines, demoted) → Why OptiMiles Exists → FAQ → Final CTA. Goal-oriented CTA copy throughout. Decision logged: `2026-06-21-landing-page-outcome-redesign.md`.
- New section components under `src/components/sections/`: `HeroFlow`, `DreamOutcomes`, `HowItWorks`, `TrustPillars`, `StrategyOutput`, `EcosystemMarquee`, `BuiltFor` (plus the pre-existing `FeatureTabs`, `SupportedCards`, `Faq`).
- New reusable animation primitives `src/components/ui/`: `Reveal` (scroll-reveal via IntersectionObserver) and `CountUp` (rAF count-up). Both respect `prefers-reduced-motion`. **Still no animation library** — CSS/IO only.
- Simulator rebuilt: added timeline, preferred-airline, multi-select current-cards inputs; count-up animated results.
- Supported-cards carousel rebuilt: 4s autoplay, pause-on-hover, drag/touch, active-card scaling — self-contained, still no embla/swiper.
- **Real card photography + curated example wallet** (`supported-cards.tsx`, `public/cards/`): cards render real art via `next/image` (`fill`/`object-cover` + bottom scrim) when an `image` is set, else icon+gradient fallback. The "cards you already carry" section is now a **4-card illustrative example, all active with real photos**: HDFC Infinia, HDFC Diners Club Black, HDFC Regalia Gold, HSBC TravelOne. (Earlier intermediate states with HSBC Premier and Axis/Amex coming-soon placeholders were trimmed away.) **SBI removed from the frontend** (ecosystem marquee badge + FAQ supported-cards answer). Decision logged: `2026-06-21-supported-cards-photos-and-scope.md`.
- **Canonical card scope reconciled:** root `CLAUDE.md` "Initial Supported Cards" added HDFC Regalia Gold + HSBC TravelOne (SBI Cashback kept in product scope, removed from UI only); `docs/prd/mvp_scope_1.md` added HSBC TravelOne, removed SBI Aurum + ICICI Emeralde. The 4-card wallet is a deliberate UI subset of the MVP scope, not drift.
- FAQ expanded to the brief's 7 questions (kept generic).
- `globals.css`: new `bg-hero-field`, `bg-starfield`, `.reveal`, `.hero-flow-line` utilities + `hero-drift`/`starfield-drift`/`hero-flow-draw` keyframes, all gated behind `prefers-reduced-motion`.
- Earlier same-day work (still current): full `OptiMILES`→`OptiMiles` rebrand, all named-partner copy stripped, dark native-control fix (`color-scheme: dark`), in-repo `Tabs`/`Accordion`/`Carousel` primitives, `SiteNav`/`SiteFooter`/`Brand`, `/login`+`/signup` with shared `AuthForm`.
- `npm run build` and `npx eslint src` both pass clean; live dev-server render returned HTTP 200 with all sections present.

### In progress
- Auth forms are **front-end only** — submit handler is a `setTimeout` stub, not wired to a real backend auth route.
- Redesign is build/lint/HTTP-200 verified but **not yet eyeballed in a browser** — a human visual scroll-through of the animations and gradient placeholders is still pending (required per root `CLAUDE.md` before calling UI work fully verified).
- `testimonials.tsx` and `STATS` were dropped from the homepage (not in the new brief) — `testimonials.tsx` remains in-repo unused rather than deleted.

### Next up
- Visual browser pass of the redesigned homepage (desktop + mobile): animations, marquee, autoplay carousel, simulator count-up, mobile nav, and the new hero flow card (line-draw, node stagger, 2-col balance vs. headline; check card height feels right next to the copy).
- (Optional) Add Axis/Amex card photos to `public/cards/` if they should appear in the wallet example — they're in MVP scope but not currently shown.
- Swap gradient placeholders in `DreamOutcomes` for real photos once the user supplies them to `/public`.
- Wire `AuthForm` to a real backend endpoint once one exists.

---

## Docs / Product

### Done
- `/docs` structure established: `prd`, `architecture`, `research`, `ux`, `decisions`, `prompts`.
- `docs/prd/mvp_scope_1.md`, `docs/architecture/{ai-tooling-setup-v1,db-schema-v1}.md`, `docs/research/singapore_airlines_krisflyer_indian_credit_card_research_v1.md`, `docs/ux/landing-page-v1.md`, `docs/prompts/template.md`.
- Decision log entries: `2026-06-21-frontend-mvp-cleanup.md`, `2026-06-21-multi-tool-agent-skill-expansion.md`, `2026-06-21-landing-page-outcome-redesign.md`, `2026-06-21-supported-cards-photos-and-scope.md`.
- Claude Code skills: `codebase-design`, `diagnosing-bugs`, `docs-sync`, `domain-modeling`, `handoff`, `tdd`, `to-issues`, `to-prd`, `tracker-sync` (this one).
- Subagents: `backend-reviewer`, `frontend-reviewer`, `feature-discussion`, `prd-writer`.

### In progress
- Nothing active. (The earlier frontend rebrand/homepage/auth session is now covered by `2026-06-21-frontend-mvp-cleanup.md`; the redesign by `2026-06-21-landing-page-outcome-redesign.md`.)

### Next up
- Nothing pending on the docs side.

---

## Last session notes

Redesigned the homepage to be **outcome-first** instead of engine-first, preserving the dark/gold luxury aesthetic. Confirmed two scope calls with the user up front: keep brand names generic (honoring the earlier cleanup decision) and stay dependency-free (CSS/IntersectionObserver animation, no Framer Motion; gradient placeholders instead of real photography). Added six new section components (DreamOutcomes, HowItWorks, TrustPillars, StrategyOutput, EcosystemMarquee, BuiltFor) and two reusable animation primitives (Reveal, CountUp), rebuilt the simulator (more inputs + count-up), the supported-cards carousel (autoplay/drag/scaling), and the FAQ (7 questions). New `globals.css` utilities for the hero gradient field, starfield, and scroll-reveal, all gated on `prefers-reduced-motion`. Verified with `next build` + `eslint` (clean) and a live HTTP-200 render. Logged the decision as `2026-06-21-landing-page-outcome-redesign.md`. **Still pending:** a human visual browser pass of the animations, and real photography to replace the gradient placeholders.

Follow-up (same day): the user flagged the hero right side as too empty. Offered three dependency-free options (live strategy card / animated goal→path flow / floating card stack); user picked the **goal→path flow**. Built `HeroFlow` (`src/components/sections/hero-flow.tsx`) — a glass card showing Your goal → Your cards → Transfer path → Redemption with a self-drawing gold connector, staggered node reveals, and a CountUp payoff footer — and converted the hero to a 2-col grid that stacks on mobile. Added `.hero-flow-line` + `hero-flow-draw` to `globals.css` (reduced-motion gated). Re-verified `eslint` + `next build` clean.

Then wired **real card photography** into `SupportedCards` and changed the supported-card set. Cards render real art (`next/image` fill + scrim) when an `image` is set, else icon+gradient. Final set: 5 photo cards (HDFC Infinia, Diners Club Black, Regalia Gold, HSBC Premier, HSBC TravelOne) + 3 coming-soon (Axis Atlas, Axis Magnus, Amex Platinum Travel); dropped SBI Cashback + off-scope filler. This **widens MVP card scope** beyond root `CLAUDE.md` (added HSBC ×2 + Regalia Gold, dropped SBI Cashback) — confirmed with the user and logged as `2026-06-21-supported-cards-photos-and-scope.md`. Photos copied from `~/Downloads/cc-photos/` into `public/cards/` (originals archived in `public/cards/_originals/`).

After a visual review the wallet was tightened to a **4-card example** (HDFC Infinia, Diners Club Black, Regalia Gold, HSBC TravelOne — all active, real photos); HSBC Premier and the Axis/Amex coming-soon placeholders were removed. **SBI removed from the frontend** (marquee + FAQ). Then **reconciled the canonical card scope** per the user: `CLAUDE.md` gained HDFC Regalia Gold + HSBC TravelOne (SBI kept in product scope, UI-only removal); PRD gained HSBC TravelOne and dropped SBI Aurum + ICICI Emeralde. The 4-card wallet is an intentional UI subset of MVP scope. All build/lint clean. Decision fully captured in `2026-06-21-supported-cards-photos-and-scope.md`.
