# OptiMiles — Project Tracker

A living snapshot of where the project actually stands right now — not a changelog. This file is **overwritten in place** after any session that does real work in `backend/`, `frontend/`, or `docs/`; it should never grow into an endless history. For *why* a decision was made, see `docs/decisions/` — that log is permanent and never rewritten. This file is disposable and just reflects current truth.

Maintained by the `tracker-sync` skill (`.claude/skills/tracker-sync/SKILL.md`). Read this file before starting new work in any chat; refresh it before ending one.

---

**Last updated:** 2026-06-27 — Supported-cards reworked into a static all-visible grid (5 cards, landscape, uncropped, no scroll); Amex Platinum Travel added; Infinia/Amex art refreshed. Prior same-day: design-sync to claude.ai/design (6 components, all `match`), hero scroll-bug fix (user-confirmed), Storybook, root README.

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
- **Motion** (`src/components/ui/motion.tsx`, `hero.tsx`, `hero-flow.tsx`, `how-it-works.tsx`, `simulator-scene.tsx`): the redesign adopted **`motion` (Framer Motion v12, a real dependency)**. Hero is a pin-and-release stage (scale/blur/fade). **The hero exit is driven off raw document `scrollY` in pixels** (`useScroll().scrollY` → `useTransform` with clamped px thresholds at ~0.12→0.7 viewport-heights), **not** a scoped `useScroll({ target })` and **not** a fraction of the whole document — both earlier approaches were buggy: document-fraction fired the blur almost immediately on the tall page, and `{ target }` mis-read its progress before first-paint layout and left the hero invisible/blank until the first scroll. `scrollY` reliably starts at 0 on mount, so the hero is crisp+opaque at rest. `simulator-scene.tsx` is a normal freely-scrollable block with a one-time `whileInView` entrance + sticky intro copy (an earlier ~260vh *pinned* simulator scene was reverted — it hijacked the wheel and clipped the expanding results). All effects collapse to static under `prefers-reduced-motion`. The older CSS/IntersectionObserver primitives (`Reveal`, `CountUp`) still exist alongside.
- **Hero visual — goal→path flow** (`src/components/sections/hero-flow.tsx`): glass card showing the product journey (Your goal → Your cards → Transfer path → Redemption) connected by a self-drawing gold line, staggered node reveal, footer payoff (CountUp 92,000 projected miles + "High confidence"). Generic brand names only.
- Section components under `src/components/sections/`: `Hero`, `HeroFlow`, `SimulatorScene`, `DreamOutcomes`, `HowItWorks`, `TrustPillars`, `StrategyOutput`, `EcosystemMarquee`, `BuiltFor`, `FeatureTabs`, `SupportedCards`, `Faq`, `section-shell`.
- Simulator (`goal-simulator.tsx`): timeline, preferred-airline, multi-select current-cards inputs; count-up animated results. Header eyebrow simplified now that the section owns the heading. Remains a **static mock** (hardcoded destinations/mile counts) pending the real Simulation Engine.
- **Real card photography + curated example wallet** (`supported-cards.tsx`, `public/cards/`): a **static responsive grid (no carousel)** — 5-up on desktop, 3 on tablet, 2 on mobile, all cards visible at once with **no horizontal scroll**. Each tile is a fixed credit-card aspect ratio (`1.586:1`) showing the full art via `object-contain` on a dark plate (so nothing is cropped and transparent-edge PNGs blend in — no white box); the name/tier label + Active badge sit **below** each card (no overlaid scrim). The wallet is a **5-card illustrative example, all active with real landscape photos**: HDFC Infinia, HDFC Diners Club Black, HDFC Regalia Gold, HSBC TravelOne, Amex Platinum Travel. (Infinia + Amex art refreshed to new high-res images; a portrait HSBC "T1" render was tried then dropped — it couldn't be a clean landscape tile, so the existing landscape `hsbc-travelone.jpg` was kept.) An earlier autoplay/drag carousel with `object-cover` + bottom scrim was replaced because `object-cover` cropped the wide card logos. **SBI removed from the frontend** (ecosystem marquee badge + FAQ supported-cards answer). Decision logged: `2026-06-21-supported-cards-photos-and-scope.md`.
- **Canonical card scope reconciled:** root `CLAUDE.md` "Initial Supported Cards" added HDFC Regalia Gold + HSBC TravelOne (SBI Cashback kept in product scope, removed from UI only); `docs/prd/mvp_scope_1.md` added HSBC TravelOne, removed SBI Aurum + ICICI Emeralde. The 5-card wallet (incl. Amex Platinum Travel, already in both CLAUDE.md and the PRD) is a deliberate UI subset of the MVP scope, not drift.
- FAQ expanded to the brief's 7 questions (kept generic).
- `globals.css`: `bg-hero-field`, `bg-starfield` (now static), `.reveal`, `.hero-flow-line` utilities + `hero-drift`/`hero-flow-draw` keyframes, gated behind `prefers-reduced-motion`.
- **Storybook (Vite adapter)** set up over the frontend: Storybook 10.4.6 + `@storybook/nextjs-vite` + `@tailwindcss/vite`, config in `.storybook/` (`main.ts` wires Tailwind v4 + `@/` alias; `preview.ts` imports `globals.css`, forces the dark-only `.dark` theme + a font-var shim). 28 stories across `button`/`badge`/`card`/`input` primitives + `hero-flow`/`trust-pillars` sections, written against real component APIs. Build + dev both clean. `/storybook-static` gitignored. Decision logged: `2026-06-27-storybook-setup-for-design-sync.md`. **(Dark/gold theme + Fraunces now confirmed rendering via the design-sync compare run, below — pixel check no longer pending.)**
- **Design system synced to claude.ai/design** (project "OptiMiles Design System", `8aa116b0-…`): 6 components (Button, Badge, Card, Input, HeroFlow, TrustPillars) imported via `/design-sync`'s high-fidelity Storybook path — all stories graded `match` against the reference Storybook, uploaded with the Fraunces webfont + a `conventions.md` header for the design agent. Required building a **library export surface** the app lacked: `src/lib-entry.ts` barrel (relative re-exports), emitted `.d.ts` (`tsconfig.dts.json` → `dist/types`, `types` field in `package.json`), and `DsThemeProvider` for the dark theme. Committed config under `.design-sync/` (config/NOTES/conventions/fonts). Decision logged: `2026-06-27-design-sync-claude-design-import.md`.
- Earlier same-day work (still current): full `OptiMILES`→`OptiMiles` rebrand, all named-partner copy stripped, dark native-control fix (`color-scheme: dark`), in-repo `Tabs`/`Accordion`/`Carousel` primitives, `SiteNav`/`SiteFooter`/`Brand`, `/login`+`/signup` with shared `AuthForm`.
- `npm run build` and `npx eslint src` both pass clean; live dev-server render returned HTTP 200 with all sections present.
- **Site footer polish** (`site-footer.tsx`): left brand block gained two icon badges (email + website link) in the existing gold-pill style, giving it visual weight to match the link columns. Bottom bar got a small gold accent dot next to the tagline and reflows copyright-first on mobile. Copy in `faq.tsx`, `feature-tabs.tsx`, `testimonials.tsx`, `trust-pillars.tsx` had em-dashes stripped (user edit, cosmetic only). Verified via Playwright screenshot + zero console errors — visually confirmed, not just build-checked.
- **Known constraint:** `lucide-react` is pinned to v1.21 (per `frontend/AGENTS.md`), which **removed all brand/logo icons** (`Twitter`, `Linkedin`, `Github`, `Instagram`, `Facebook`, `Youtube`, etc. don't exist in this version — importing them crashes the dev server with a module-export error). Only generic shape icons remain (`Mail`, `Globe`, `Send`, `MessageCircle`, `Rss`, ...). Any future social-link UI must use generic icons, not brand icons.

### In progress
- Auth forms are **front-end only** — submit handler is a `setTimeout` stub, not wired to a real backend auth route.
- Product-first/edge-to-edge redesign is `tsc`/`eslint`/HTTP-200 verified; the **hero pin-and-release is now visually confirmed by the user** (after the scroll-bug fix). The **rest** of the page still needs a human scroll-through (simulator entrance, full-bleed rhythm, marquee, autoplay carousel, mobile nav) per root `CLAUDE.md`.
- `testimonials.tsx` remains in-repo unused (dropped from the homepage, not deleted).
- **Flagged drift (not yet reconciled):** the `2026-06-21` redesign decision recorded the project as "dependency-free, no Framer Motion," but the `2026-06-26` redesign adopted `motion/react`. That decision doc needs reconciling — see `2026-06-26-...fullbleed.md` "Notes / follow-ups."

### Next up
- Visual browser pass (desktop + mobile) of the **rest** of the redesigned homepage (hero now confirmed): simulator section entrance + that it doesn't clip expanding results, full-bleed gutter rhythm, marquee, autoplay carousel, mobile nav.
- (If more components should appear in claude.ai/design) story them, add to `src/lib-entry.ts`, re-emit `.d.ts`, rebuild the reference, and re-run `/design-sync` (re-sync risks in `.design-sync/NOTES.md`).
- (Optional) Add Axis/Amex card photos to `public/cards/` if they should appear in the wallet example.
- Swap gradient placeholders in `DreamOutcomes` for real photos once supplied to `/public`.
- Wire `AuthForm` to a real backend endpoint once one exists.
- Reconcile the "no animation library" claim across the `2026-06-21` decision doc now that Framer Motion is in use.

---

## Docs / Product

### Done
- `/docs` structure established: `prd`, `architecture`, `research`, `ux`, `decisions`, `prompts`.
- `docs/prd/mvp_scope_1.md`, `docs/architecture/{ai-tooling-setup-v1,db-schema-v1}.md`, `docs/research/singapore_airlines_krisflyer_indian_credit_card_research_v1.md`, `docs/ux/landing-page-v1.md`, `docs/prompts/template.md`.
- Decision log entries: `2026-06-21-frontend-mvp-cleanup.md`, `2026-06-21-multi-tool-agent-skill-expansion.md`, `2026-06-21-landing-page-outcome-redesign.md`, `2026-06-21-supported-cards-photos-and-scope.md`, `2026-06-26-landing-page-product-first-fullbleed.md`, `2026-06-27-storybook-setup-for-design-sync.md`, `2026-06-27-design-sync-claude-design-import.md`.
- Root `README.md` added (project overview, honest Phase-0 status table, MVP scope, architecture, tech stack, getting-started, docs map).
- `CLAUDE.md` gained a "Skills & Agents — When To Use Them" section (skill/agent triggers); `docs-sync` made an unconditional default after any build/change/decision. The redundant `.cursor/rules` mirror of the `.claude` skills was removed.
- Claude Code skills: `brandkit`, `codebase-design`, `design-taste-frontend-v1`, `diagnosing-bugs`, `docs-sync`, `domain-modeling`, `handoff`, `tdd`, `to-issues`, `to-prd`, `tracker-sync`.
- Subagents: `backend-reviewer`, `frontend-reviewer`, `feature-discussion`, `prd-writer`.

### In progress
- Nothing active. (The earlier frontend rebrand/homepage/auth session is now covered by `2026-06-21-frontend-mvp-cleanup.md`; the redesign by `2026-06-21-landing-page-outcome-redesign.md`.)

### Next up
- Nothing pending on the docs side.

---

## Last session notes

Reworked the "cards you already carry" section (`supported-cards.tsx`) on user feedback. Two new card images (HDFC Infinia + Amex Platinum Travel, refreshed high-res) were dropped into `public/cards/` and **Amex Platinum Travel was added** as a 5th card. The user supplied a new HSBC "T1" render, but it was a **portrait card on a checkered/transparent background** — first attempt placed it `object-contain` with a `portrait` branch, but the user then asked for **all-landscape, no white background, and no horizontal scroll with every card fitting the window**, which the portrait T1 couldn't satisfy. So: reverted HSBC to the existing landscape `hsbc-travelone.jpg`, deleted the cropped T1, and **replaced the autoplay/drag carousel with a static responsive grid** (5-up desktop → 2-up mobile, `object-contain` on a dark plate at `1.586:1`, labels below each card, no scrim). This fixed the original cropping (e.g. "C Infinia") that `object-cover` caused. `tsc`/eslint/HTTP-200 clean; user visually confirmed ("perfect"). Amex was already in CLAUDE.md + the PRD, so no scope drift. Bug fix / UI polish — no decision-log entry. (Earlier same day: design-sync to claude.ai/design — see `2026-06-27-design-sync-claude-design-import.md`; and a hero scroll-bug fix in `hero.tsx`.)

### Prior reconciliation (still current)

The tracker had earlier gone stale by three commits; the product-first/edge-to-edge landing redesign at HEAD (`824619a`) is captured in the Frontend section above and in `2026-06-26-landing-page-product-first-fullbleed.md`. Note the flagged, still-unreconciled drift: the project now uses Framer Motion despite an earlier "no animation library" decision.
