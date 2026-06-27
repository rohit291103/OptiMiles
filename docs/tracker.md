# OptiMiles — Project Tracker

A living snapshot of where the project actually stands right now — not a changelog. This file is **overwritten in place** after any session that does real work in `backend/`, `frontend/`, or `docs/`; it should never grow into an endless history. For *why* a decision was made, see `docs/decisions/` — that log is permanent and never rewritten. This file is disposable and just reflects current truth.

Maintained by the `tracker-sync` skill (`.claude/skills/tracker-sync/SKILL.md`). Read this file before starting new work in any chat; refresh it before ending one.

---

**Last updated:** 2026-06-27 — Tracker reconciled after three uncaptured commits: product-first, edge-to-edge landing-page redesign (Goal Simulator promoted to section 2; `Bleed`/`Inner` primitives; `page-frame.tsx` removed; Framer Motion now a real dependency).

## Snapshot

Phase 0 (Product Definition & Architecture, per root `CLAUDE.md`). Backend has no code yet — schema and engine work hasn't started. Frontend is now a **product-first, edge-to-edge** marketing site: the live Goal Simulator sits directly under the hero (section 2, Replit-style) so visitors can use the product before any marketing, then outcomes/trust/strategy/cards/ecosystem/capabilities/mission/FAQ/CTA scroll below — all true full-bleed (no centered `max-w` cage), on the dark/gold design system, plus front-end-only login/signup pages. **Motion is no longer dependency-free** — the redesign adopted `motion` (Framer Motion v12) for the hero pin-and-release and simulator entrance, alongside the existing CSS/IntersectionObserver primitives. Docs and Claude Code project infra (skills, subagents) are actively being built out alongside the product itself.

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
- **Product-first, edge-to-edge landing page** (`src/app/page.tsx`): the live Goal Simulator is promoted to **section 2, directly under the hero** (Replit pattern — usable on first scroll, not buried mid-page). Full section order: Hero → **Goal Simulator** → Dream Outcomes → How It Works → Why Trust (4-up pillars) → Strategy Output → Cards You Carry → Ecosystem marquee → Built For → Capabilities (engines, demoted) → Why OptiMiles Exists → FAQ → Final CTA. Truly **full-bleed** — no centered `max-w` cage; horizontal gutter lives only on `Inner` (fluid pad), readable line-length restored locally via `max-w-prose`/`Measure`. Decision logged: `2026-06-26-landing-page-product-first-fullbleed.md` (supersedes the `2026-06-21` outcome-first layout).
- **Layout primitives** `src/components/sections/section-shell.tsx`: `Bleed` (full viewport width, optional `banded` tint + hairline for alternating rhythm, optional `id` w/ `scroll-mt`), `Inner` (fluid-gutter content wrapper), `Measure` (readable-width helper). `page.tsx` sections migrated onto these.
- **`page-frame.tsx` deleted** and `bg-starfield` made a static texture — the decorative fixed side-rails with travelling gold dots were built for the old centered column and looked wrong / distracting in the edge-to-edge layout.
- **Motion** (`src/components/ui/motion.tsx`, `hero.tsx`, `hero-flow.tsx`, `how-it-works.tsx`, `simulator-scene.tsx`): the redesign adopted **`motion` (Framer Motion v12, a real dependency)**. Hero is a pin-and-release stage (scale/blur/fade via `useScroll`/`useTransform`); `simulator-scene.tsx` is a normal freely-scrollable block with a one-time `whileInView` entrance + sticky intro copy (an earlier ~260vh *pinned* simulator scene was reverted — it hijacked the wheel and clipped the expanding results). All effects collapse to static under `prefers-reduced-motion`. The older CSS/IntersectionObserver primitives (`Reveal`, `CountUp`) still exist alongside.
- **Hero visual — goal→path flow** (`src/components/sections/hero-flow.tsx`): glass card showing the product journey (Your goal → Your cards → Transfer path → Redemption) connected by a self-drawing gold line, staggered node reveal, footer payoff (CountUp 92,000 projected miles + "High confidence"). Generic brand names only.
- Section components under `src/components/sections/`: `Hero`, `HeroFlow`, `SimulatorScene`, `DreamOutcomes`, `HowItWorks`, `TrustPillars`, `StrategyOutput`, `EcosystemMarquee`, `BuiltFor`, `FeatureTabs`, `SupportedCards`, `Faq`, `section-shell`.
- Simulator (`goal-simulator.tsx`): timeline, preferred-airline, multi-select current-cards inputs; count-up animated results. Header eyebrow simplified now that the section owns the heading. Remains a **static mock** (hardcoded destinations/mile counts) pending the real Simulation Engine.
- Supported-cards carousel rebuilt: 4s autoplay, pause-on-hover, drag/touch, active-card scaling — self-contained, still no embla/swiper.
- **Real card photography + curated example wallet** (`supported-cards.tsx`, `public/cards/`): cards render real art via `next/image` (`fill`/`object-cover` + bottom scrim) when an `image` is set, else icon+gradient fallback. The "cards you already carry" section is now a **4-card illustrative example, all active with real photos**: HDFC Infinia, HDFC Diners Club Black, HDFC Regalia Gold, HSBC TravelOne. (Earlier intermediate states with HSBC Premier and Axis/Amex coming-soon placeholders were trimmed away.) **SBI removed from the frontend** (ecosystem marquee badge + FAQ supported-cards answer). Decision logged: `2026-06-21-supported-cards-photos-and-scope.md`.
- **Canonical card scope reconciled:** root `CLAUDE.md` "Initial Supported Cards" added HDFC Regalia Gold + HSBC TravelOne (SBI Cashback kept in product scope, removed from UI only); `docs/prd/mvp_scope_1.md` added HSBC TravelOne, removed SBI Aurum + ICICI Emeralde. The 4-card wallet is a deliberate UI subset of the MVP scope, not drift.
- FAQ expanded to the brief's 7 questions (kept generic).
- `globals.css`: `bg-hero-field`, `bg-starfield` (now static), `.reveal`, `.hero-flow-line` utilities + `hero-drift`/`hero-flow-draw` keyframes, gated behind `prefers-reduced-motion`.
- Earlier same-day work (still current): full `OptiMILES`→`OptiMiles` rebrand, all named-partner copy stripped, dark native-control fix (`color-scheme: dark`), in-repo `Tabs`/`Accordion`/`Carousel` primitives, `SiteNav`/`SiteFooter`/`Brand`, `/login`+`/signup` with shared `AuthForm`.
- `npm run build` and `npx eslint src` both pass clean; live dev-server render returned HTTP 200 with all sections present.
- **Site footer polish** (`site-footer.tsx`): left brand block gained two icon badges (email + website link) in the existing gold-pill style, giving it visual weight to match the link columns. Bottom bar got a small gold accent dot next to the tagline and reflows copyright-first on mobile. Copy in `faq.tsx`, `feature-tabs.tsx`, `testimonials.tsx`, `trust-pillars.tsx` had em-dashes stripped (user edit, cosmetic only). Verified via Playwright screenshot + zero console errors — visually confirmed, not just build-checked.
- **Known constraint:** `lucide-react` is pinned to v1.21 (per `frontend/AGENTS.md`), which **removed all brand/logo icons** (`Twitter`, `Linkedin`, `Github`, `Instagram`, `Facebook`, `Youtube`, etc. don't exist in this version — importing them crashes the dev server with a module-export error). Only generic shape icons remain (`Mail`, `Globe`, `Send`, `MessageCircle`, `Rss`, ...). Any future social-link UI must use generic icons, not brand icons.

### In progress
- Auth forms are **front-end only** — submit handler is a `setTimeout` stub, not wired to a real backend auth route.
- Product-first/edge-to-edge redesign is `tsc`/`eslint`/HTTP-200 verified but **not yet eyeballed in a browser** — a human visual scroll-through (hero pin-and-release, simulator entrance, full-bleed rhythm, mobile) is still pending per root `CLAUDE.md`.
- `testimonials.tsx` remains in-repo unused (dropped from the homepage, not deleted).
- **Flagged drift (not yet reconciled):** the `2026-06-21` redesign decision recorded the project as "dependency-free, no Framer Motion," but the `2026-06-26` redesign adopted `motion/react`. That decision doc needs reconciling — see `2026-06-26-...fullbleed.md` "Notes / follow-ups."

### Next up
- Visual browser pass (desktop + mobile) of the redesigned homepage: hero pin-and-release scale/blur/fade, simulator section entrance + that it doesn't clip expanding results, full-bleed gutter rhythm, marquee, autoplay carousel, mobile nav.
- (Optional) Add Axis/Amex card photos to `public/cards/` if they should appear in the wallet example.
- Swap gradient placeholders in `DreamOutcomes` for real photos once supplied to `/public`.
- Wire `AuthForm` to a real backend endpoint once one exists.
- Reconcile the "no animation library" claim across the `2026-06-21` decision doc now that Framer Motion is in use.

---

## Docs / Product

### Done
- `/docs` structure established: `prd`, `architecture`, `research`, `ux`, `decisions`, `prompts`.
- `docs/prd/mvp_scope_1.md`, `docs/architecture/{ai-tooling-setup-v1,db-schema-v1}.md`, `docs/research/singapore_airlines_krisflyer_indian_credit_card_research_v1.md`, `docs/ux/landing-page-v1.md`, `docs/prompts/template.md`.
- Decision log entries: `2026-06-21-frontend-mvp-cleanup.md`, `2026-06-21-multi-tool-agent-skill-expansion.md`, `2026-06-21-landing-page-outcome-redesign.md`, `2026-06-21-supported-cards-photos-and-scope.md`, `2026-06-26-landing-page-product-first-fullbleed.md`.
- `CLAUDE.md` gained a "Skills & Agents — When To Use Them" section (skill/agent triggers); `docs-sync` made an unconditional default after any build/change/decision. The redundant `.cursor/rules` mirror of the `.claude` skills was removed.
- Claude Code skills: `brandkit`, `codebase-design`, `design-taste-frontend-v1`, `diagnosing-bugs`, `docs-sync`, `domain-modeling`, `handoff`, `tdd`, `to-issues`, `to-prd`, `tracker-sync`.
- Subagents: `backend-reviewer`, `frontend-reviewer`, `feature-discussion`, `prd-writer`.

### In progress
- Nothing active. (The earlier frontend rebrand/homepage/auth session is now covered by `2026-06-21-frontend-mvp-cleanup.md`; the redesign by `2026-06-21-landing-page-outcome-redesign.md`.)

### Next up
- Nothing pending on the docs side.

---

## Last session notes

This session was a **tracker reconciliation** — no new product code was written. The tracker had gone stale: it last reflected commit `23c7334` (2026-06-22 footer polish) but three further commits had landed since (`5e3603c` WIP bento/copy checkpoint, `c49111e` CLAUDE.md skills section + frontend redesign carry-forward, `824619a` the product-first/edge-to-edge landing redesign at HEAD). The headline change is `824619a`: the live Goal Simulator was promoted to **section 2 directly under the hero** (Replit pattern), the centered `max-w` column was removed in favour of **true edge-to-edge** sections via new `Bleed`/`Inner`/`Measure` primitives in `section-shell.tsx`, `page-frame.tsx` was deleted, and — notably — the project adopted **`motion` (Framer Motion v12)** for the hero pin-and-release and simulator entrance, which contradicts the earlier "dependency-free, no animation library" claim (flagged for reconciliation, not yet resolved). An earlier pinned-scroll simulator scene was reverted because it hijacked the wheel and clipped expanding results. All of this is captured in decision doc `2026-06-26-landing-page-product-first-fullbleed.md`. The working tree currently has two uncommitted deletions of mirror `frontend/.agents/skills/.../SKILL.md` files. Verification carried over from the decision doc (`tsc`/`eslint`/HTTP-200); a human visual browser pass is still pending.
