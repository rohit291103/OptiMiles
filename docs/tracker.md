# OptiMiles — Project Tracker

A living snapshot of where the project actually stands right now — not a changelog. This file is **overwritten in place** after any session that does real work in `backend/`, `frontend/`, or `docs/`; it should never grow into an endless history. For *why* a decision was made, see `docs/decisions/` — that log is permanent and never rewritten. This file is disposable and just reflects current truth.

Maintained by the `tracker-sync` skill (`.claude/skills/tracker-sync/SKILL.md`). Read this file before starting new work in any chat; refresh it before ending one.

---

**Last updated:** 2026-06-21 — Frontend rebrand (OptiMiles casing + removal of all Singapore Airlines/KrisFlyer/MVP copy), homepage rebuild, login/signup pages.

## Snapshot

Phase 0 (Product Definition & Architecture, per root `CLAUDE.md`). Backend has no code yet — schema and engine work hasn't started. Frontend has gone from a single shallow placeholder page to a fuller marketing site (hero, how-it-works, feature tabs, supported-cards carousel, simulator, testimonials, FAQ) plus front-end-only login/signup pages, all on the existing dark/gold design system. Docs and Claude Code project infra (skills, subagents) are actively being built out alongside the product itself.

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
- Full rebrand: `OptiMILES` → `OptiMiles` everywhere; all literal "Singapore Airlines", "KrisFlyer", and "MVP" copy removed from UI, including the footer (verified via repo-wide grep — zero matches outside this doc).
- Dark theme native-control fix: `color-scheme: dark` + themed scrollbar so browser-native scrollbar/select/inputs don't render in light mode against the dark UI.
- Homepage (`src/app/page.tsx`) rebuilt with real sections: hero + stats bar, "how it works" (3 engines), feature tabs, supported-cards carousel (18-card roadmap, Active vs. Coming soon), goal simulator, testimonials carousel, FAQ accordion, final CTA, footer.
- New dependency-free UI primitives: `Tabs`, `Accordion`, `Carousel` (CSS scroll-snap, no embla/swiper) in `src/components/ui/`.
- New shared components: `SiteNav` (sticky, mobile menu), `SiteFooter`, `Brand`.
- New section components under `src/components/sections/`: `FeatureTabs`, `SupportedCards`, `Testimonials`, `Faq`.
- Goal simulator rewritten: cabin-class selector (Economy/Business/First), progress bar, generic "frequent-flyer transfer" wording instead of naming KrisFlyer.
- Auth flow built: `/login` and `/signup` routes, split-screen `AuthShell`, shared `AuthForm` (Google/Apple buttons, password show/hide, signup terms checkbox, loading state).
- `npm run build` and `npx eslint src` both pass clean.

### In progress
- Auth forms are **front-end only** — submit handler is a `setTimeout` stub, not wired to a real backend auth route.
- Live dev-server/browser verification of the new homepage, mobile nav, carousels, accordion, and auth pages has not been done yet (only build + lint were run). Per root `CLAUDE.md`, this is required before calling the UI work fully verified.

### Next up
- Start `npm run dev` and visually check the golden paths above (desktop + mobile) in a real browser.
- Wire `AuthForm` to a real backend endpoint once one exists.
- File a `docs/decisions/` entry for this rebrand + homepage rebuild session (not yet logged).

---

## Docs / Product

### Done
- `/docs` structure established: `prd`, `architecture`, `research`, `ux`, `decisions`, `prompts`.
- `docs/prd/mvp_scope_1.md`, `docs/architecture/{ai-tooling-setup-v1,db-schema-v1}.md`, `docs/research/singapore_airlines_krisflyer_indian_credit_card_research_v1.md`, `docs/ux/landing-page-v1.md`, `docs/prompts/template.md`.
- Decision log entries: `2026-06-21-frontend-mvp-cleanup.md`, `2026-06-21-multi-tool-agent-skill-expansion.md`.
- Claude Code skills: `codebase-design`, `diagnosing-bugs`, `docs-sync`, `domain-modeling`, `handoff`, `tdd`, `to-issues`, `to-prd`, `tracker-sync` (this one).
- Subagents: `backend-reviewer`, `frontend-reviewer`, `feature-discussion`, `prd-writer`.

### In progress
- No decision log yet for the frontend rebrand/homepage/auth session described above.

### Next up
- Log that decision once filed.

---

## Last session notes

Rebranded the entire frontend from "OptiMILES" to "OptiMiles" and stripped every "Singapore Airlines / KrisFlyer / MVP" UI reference (hero, footer, simulator copy, metadata). Rebuilt the homepage from a single shallow page into a full marketing page with hero+stats, how-it-works, a 4-tab feature showcase, a supported-cards carousel, the (enhanced) goal simulator, a testimonials carousel, an FAQ accordion, and a real footer — using only carousel/tabs/accordion primitives built in-repo (no new npm deps). Added `/login` and `/signup` pages with a shared front-end-only `AuthForm`. Verified with `next build` + `eslint`, both clean. **Not yet done:** a real browser/dev-server check of the new pages, and wiring auth to a backend.
