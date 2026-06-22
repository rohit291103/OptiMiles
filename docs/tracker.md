# OptiMiles — Project Tracker

A living snapshot of where the project actually stands right now — not a changelog. This file is **overwritten in place** after any session that does real work in `backend/`, `frontend/`, or `docs/`; it should never grow into an endless history. For *why* a decision was made, see `docs/decisions/` — that log is permanent and never rewritten. This file is disposable and just reflects current truth.

Maintained by the `tracker-sync` skill (`.claude/skills/tracker-sync/SKILL.md`). Read this file before starting new work in any chat; refresh it before ending one.

---

**Last updated:** 2026-06-22 — Site footer polished (brand social icons + accented bottom bar); em-dashes stripped from several section copy blocks.

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
- **Site footer polish** (`site-footer.tsx`): left brand block gained two icon badges (email + website link) in the existing gold-pill style, giving it visual weight to match the link columns. Bottom bar got a small gold accent dot next to the tagline and reflows copyright-first on mobile. Copy in `faq.tsx`, `feature-tabs.tsx`, `testimonials.tsx`, `trust-pillars.tsx` had em-dashes stripped (user edit, cosmetic only). Verified via Playwright screenshot + zero console errors — visually confirmed, not just build-checked.
- **Known constraint:** `lucide-react` is pinned to v1.21 (per `frontend/AGENTS.md`), which **removed all brand/logo icons** (`Twitter`, `Linkedin`, `Github`, `Instagram`, `Facebook`, `Youtube`, etc. don't exist in this version — importing them crashes the dev server with a module-export error). Only generic shape icons remain (`Mail`, `Globe`, `Send`, `MessageCircle`, `Rss`, ...). Any future social-link UI must use generic icons, not brand icons.

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

User flagged the footer's left brand block and bottom bar as looking unpolished next to the Product/Company/Legal columns. Added two icon badges (email, website) below the brand tagline using the existing gold-pill convention (`bg-gold/10 ring-1 ring-hairline`, hover → gold), and added a small gold accent dot to the bottom-bar tagline, reflowing copyright-first on mobile. While verifying in-browser, found the local dev server was crash-looping on an unrelated pre-existing issue: `lucide-react` is pinned to v1.21 (per `frontend/AGENTS.md`'s "not the Next.js you know" warning), which dropped all brand/logo icons — `Twitter`/`Linkedin`/etc. don't exist in this version and crash the build on import. Initial icon choices (Twitter/LinkedIn icons) were swapped to generic `Mail`/`Globe` icons with accurate labels instead. Restarted the dev server, confirmed HTTP 200, and used a throwaway Playwright script (`/tmp/pw-check`, not committed) to screenshot the footer and the full page and confirm zero console errors. Separately, the user made cosmetic copy edits across `faq.tsx`, `feature-tabs.tsx`, `testimonials.tsx`, `trust-pillars.tsx` (stripped em-dashes) and committed everything as `more-frontend` (`23c7334`).
