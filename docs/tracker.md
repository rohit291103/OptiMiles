# OptiMiles — Project Tracker

A living snapshot of where the project actually stands right now — not a changelog. This file is **overwritten in place** after any session that does real work in `backend/`, `frontend/`, or `docs/`; it should never grow into an endless history. For *why* a decision was made, see `docs/decisions/` — that log is permanent and never rewritten. This file is disposable and just reflects current truth.

Maintained by the `tracker-sync` skill (`.claude/skills/tracker-sync/SKILL.md`). Read this file before starting new work in any chat; refresh it before ending one.

---

**Last updated:** 2026-07-04 — Build-plan Phase 2 (Valuation Engine) done test-first: exact-arithmetic transfer math + Stage 5 opportunity enumeration, 26 hand-computed golden tests (70 total green). Earlier today: Phase 1 (Knowledge Engine + seeded catalog live in Supabase).

## Snapshot

**Phase 1 — Backend Foundation** (entered 2026-07-03, per root `CLAUDE.md`). Backend build is underway against `docs/architecture/backend-build-plan-v1.md`: **build-plan Phases 0 (Skeleton), 1 (Knowledge Engine + seeded catalog) and 2 (Valuation Engine) are done** — FastAPI boots, schema v1.1 + all 8 cards live in Supabase with verified round-trip, and the priced opportunity search space (Stage 5) computes from exact arithmetic with documented rounding directions. The biggest open risk: ~60% of seed rows carry `needs_verification: true` pending the user's line-by-line check against live bank pages. Next unit of work is build-plan Phase 3 (Simulation Engine). Frontend is a product-first, edge-to-edge marketing site (dark/gold, Framer Motion v12, static-mock Goal Simulator) awaiting the real backend. Repo: `github.com/rohit291103/OptiMiles`.

---

## Backend

### Done
- **Skeleton (build-plan Phase 0):** `backend/` laid out per plan §4 (`app/{domain,knowledge,valuation,simulation,optimization,ai_reasoning,pipeline,repositories,api}`, `seeds/`, `tests/`), each engine package carrying its ownership rules as a docstring. uv-managed, Python 3.13; ruff + **mypy strict** + pytest green; CI at `.github/workflows/backend-ci.yml` (path-filtered to `backend/`). FastAPI boots; `GET /health` 200 (`catalog_snapshot_version` stays null until the pipeline phase wires a DB-backed snapshot).
- **`app/domain/` shared kernel:** frozen Pydantic models for every blueprint pipeline object (intent → goal → requirement → PlanningContext → opportunities → feasibility/PortfolioAssessment → strategies → simulation → ranking → narration → FinalRecommendation) + v1.1 catalog types (`RewardCurrency`, `CurrencyTransferLink`) + canonical enums. All-frozen enforced by test.
- **Schema v1.1 live on Supabase** (project `lrmmoianbzjghlpxcisl`): Alembic migration `0001` applied and verified — 14 tables, currency-level transfer junction, lineage columns, RLS on all 7 user-scoped tables. Durable constraint: migration SQL routes through a `_execute()` splitter (asyncpg = one command per prepared statement) — never put `;` inside SQL string literals in migrations.
- **Boundary guards as tests** (`tests/unit/test_module_boundaries.py`): AST checks — `domain/` imports nothing from `app`, engines don't cross-import (except Optimization/Simulation → Valuation pure math), no LLM client outside `ai_reasoning/`.
- **Knowledge Engine (build-plan Phase 1, test-first):** `app/knowledge/` — `seed_catalog.py` (YAML → CatalogSnapshot, deterministic UUID5 ids), `versioning.py` (Decimal-normalized content-hash version: same content ⇒ same version from YAML or DB), `validation.py` (`validate_catalog()`: orphan FKs, default-category + duplicate-slug checks, ratio sanity 1:4…5:1, cashback-has-no-links negative case, KrisFlyer reach, 3-MVP-routes × business coverage — reports ALL issues at once), `goal_resolution.py` (Stage 2: city→region table; ambiguous/unknown input → ClarificationRequest, un-charted route → explicit `UnsupportedRoute`), `requirements.py` (Stage 3: locked-chart lookup, buffer ceils up, `ChartRowMissing` fails loudly), `store.py` (sole DB reader of catalog tables, ORDER BY id). Writes live in `repositories/catalog_admin.py` (idempotent upsert + deactivate-stale, never delete).
- **Seed catalog, all 8 MVP cards** (`seeds/catalog/*.yaml`): 7 currencies (HDFC split Infinia/DCB-tier vs Regalia-tier — see decision log), 2 partners (KrisFlyer + Maharaja Club), 7 transfer links (Infinia 1:1, Atlas 1:2 w/ 30k annual cap, Magnus 5:2, Amex 2:1 — golden-tested against the research doc), 13 category rules (conservative: base rate everywhere, accelerations only where documented), 5 milestones, 5 KrisFlyer award rows covering the 3 MVP routes × business. Every row carries `source` + `verified_on`; unverified values flagged `needs_verification: true`. **Loaded into live Supabase via `seeds/load_to_db.py`; order-independent round-trip verified, version `cat-ee2d1c3701e4`.** 44/44 tests green.

- **Valuation Engine (build-plan Phase 2, test-first):** `app/valuation/transfer_math.py` — the shared calculation vocabulary (formulas + units + rounding directions in the docstring): whole-block transfer conversion (`floor(points/ratio_from)×ratio_to`), min-threshold + annual-cap gating, `miles_per_100` (4dp ROUND_DOWN), cap-aware `blended_earn_rate`. `app/valuation/opportunities.py` — Stage 5: one opportunity per (eligible card × profile category), eligibility card→currency→link, default-rule fallback, valuation notes for caps/fees/default-rate, deterministic order; SBI yields zero opportunities by construction. Documented deviations (decision log `2026-07-04-phase2-...`): flat fees not folded into rates (no groundable miles→INR value); annual transfer caps applied once (exact for ≤12-month horizons). Reviewer recomputed all goldens (all matched) and caught a `normalize()`→scientific-notation serialization bug (fixed, str()-regression-tested) + unpinned cards (DCB/Regalia/HSBC now golden-asserted, incl. a D-1 currency-sharing canary). 29 hand-computed golden/boundary tests; 73/73 total, mypy strict + ruff green.

### In progress
- Nothing active — build-plan Phases 0–2 exit criteria met.

### Next up
- **USER: verify `needs_verification: true` seed rows** against live bank/KrisFlyer pages (`grep -rn "needs_verification: true" backend/seeds/catalog`) — all award-chart values + Regalia/HSBC/Atlas/Magnus/Amex details. The catalog works but is not yet trustworthy for real users. Also still open: **rotate the Supabase DB password** (pasted into chat on 2026-07-03) and update `backend/.env`.
- Phase 3 (Simulation Engine): `projector.py` monthly ledger (Stage 8). Exit: cap boundaries, milestone triggers, transfer processing delays, starting balances all fixture-tested; pure function. TDD mandatory.
- Phases 4–7 sequential (Optimization → AI Reasoning → pipeline/API → wire the frontend simulator). Each phase: fixture-tested + `backend-reviewer` pass before the next.
- Standard Magnus Group A annual cap figure + Maharaja Club links/award rows (deferred, flagged in seeds).
- (IDE nicety) Point the editor's Python interpreter at `backend/.venv/bin/python` — the root `.venv` is empty and triggers false "package not installed" hints.

---

## Frontend

### Done
- **Product-first, edge-to-edge landing page** (`src/app/page.tsx`): Goal Simulator is section 2 directly under the hero; then outcomes / how-it-works / trust pillars / strategy output / cards / ecosystem marquee / built-for / capabilities / mission / FAQ / CTA. True full-bleed (gutters only on `Inner`), dark/gold design system. Layout primitives in `section-shell.tsx` (`Bleed`/`Inner`/`Measure`). Decision: `2026-06-26-landing-page-product-first-fullbleed.md`.
- **Motion:** Framer Motion v12 (`motion`) is a real dependency. Hero pin-and-release is driven off raw document `scrollY` in pixels (clamped px thresholds) — scoped `useScroll({target})` and document-fraction variants were both buggy; don't reintroduce them. Simulator section is a normal scroll block with one-time `whileInView` entrance (a pinned ~260vh version was reverted — hijacked the wheel). All effects collapse under `prefers-reduced-motion`. CSS/IO primitives (`Reveal`, `CountUp`) coexist.
- **Supported cards**: static responsive grid (5/3/2-up, no carousel, no crop — `object-contain` on dark plates), 5-card illustrative wallet with real photos (Infinia, DCB, Regalia Gold, TravelOne, Amex Platinum Travel). SBI removed from UI only (still in product scope). Decision: `2026-06-21-supported-cards-photos-and-scope.md`.
- Simulator (`goal-simulator.tsx`) remains a **static mock** (hardcoded destinations/miles) pending the real Simulation Engine.
- **Storybook + design-sync:** Storybook 10.4.6 (`@storybook/nextjs-vite`), 28 stories; 6 components synced to claude.ai/design ("OptiMiles Design System") via the `src/lib-entry.ts` export surface. Decisions: `2026-06-27-storybook-setup-for-design-sync.md`, `2026-06-27-design-sync-claude-design-import.md`.
- Brand/chrome: OptiMiles rebrand, named-partner copy stripped, dark native controls (`color-scheme: dark`), `SiteNav`/`SiteFooter`/`Brand`, `/login`+`/signup` with shared `AuthForm`. Build + eslint clean; footer polish verified in-browser via Playwright.
- **Known constraint:** `lucide-react` pinned to v1.21 (`frontend/AGENTS.md`) — **no brand/logo icons exist in this version** (importing `Twitter`/`Github`/etc. crashes the dev server); use generic icons only.

### In progress
- Auth forms are front-end only — submit is a `setTimeout` stub awaiting a real backend auth route.
- Homepage needs a human scroll-through beyond the hero (simulator entrance + result expansion, full-bleed rhythm, marquee, mobile nav); hero pin-and-release already user-confirmed.
- `testimonials.tsx` in-repo but unused (dropped from homepage, not deleted).
- **Flagged drift:** the `2026-06-21` redesign decision doc still says "dependency-free, no Framer Motion" — contradicted by the `2026-06-26` adoption; needs reconciling.

### Next up
- Visual browser pass (desktop + mobile) of the rest of the homepage.
- Wire `AuthForm` and the Goal Simulator to real backend endpoints once they exist (build-plan Phase 7).
- (Optional) Axis/Amex card photos for the wallet; real photos for `DreamOutcomes` placeholders; more components into design-sync if needed.
- Reconcile the "no animation library" claim in the `2026-06-21` decision doc.

---

## Docs / Product

### Done
- `/docs` fully structured (`prd`, `architecture`, `research`, `ux`, `decisions`, `prompts`) with a maintained decision log (see `docs/decisions/` — filenames are the index; latest: `2026-07-04-phase1-knowledge-engine-and-seed-catalog.md`).
- **Canonical doc set for the build:** `prd/mvp-scope-v2.md` (scope; v1 superseded-bannered) · `prd/optimiles-constitution-v1.md` (tie-breaker) · `architecture/system-execution-flow-v1.md` v1.1 (the 11-stage pipeline blueprint) · `architecture/backend-build-plan-v1.md` (**backend entry point** — D-1…D-7, schema v1.1, 8 phases, seed rules; declared the last planning doc) · `architecture/core-domain-model-v1.md` (vocabulary) · engine specs (`reward-knowledge-engine-spec`, `optimization-engine-spec`, `recommendation-engine-design`) · `architecture/db-schema-v1.md` (bannered: v1.1 amendment lives in the build plan §3).
- Notion corpus (17 docs) mirrored into `/docs` with provenance headers, consolidated 7→4 engine docs, conflicts resolved (deterministic generation, bounded archetypes). User/market research in `docs/research/`, UX journey in `docs/ux/`.
- Root `CLAUDE.md` build-ready: Backend Build Rules (8 hard rules), Skills & Agents triggers, phase = Phase 1, "no more planning documents". Root `README.md` current.
- Claude Code infra: skills (`tdd`, `tracker-sync`, `docs-sync`, `codebase-design`, `diagnosing-bugs`, `domain-modeling`, `grill-me`/`grilling`, `handoff`, `to-prd`, `to-issues`, `brandkit`, …) + subagents (`backend-reviewer`, `frontend-reviewer`, `feature-discussion`, `prd-writer`).

### In progress
- Nothing active.

### Next up
- Notion-side corrections to prevent re-drift (RED-001 "AI-assisted" marker, missing simulation stage, engine→module renames) — user or Claude-via-connector.
- (Optional, non-blocking) Consolidate `db-schema-v1.md` + build-plan §3 into a `db-schema-v2.md`.

---

## Last session notes

2026-07-04 (later sitting) — **Build-plan Phase 2 (Valuation Engine) done, test-first, with the math treated as a first-class engineering artifact** (user's explicit requirement, saved to memory: exact arithmetic, deliberate rounding directions, docstring-documented formulas, hand-computed golden tests). RED: 26 failing tests with hand-computed expectations (Magnus 5:2 floors 12,345 pts → 4,938 miles; ₹200k into Infinia's ₹150k cap blends to exactly 13.32 pts/₹100; Atlas 35,000 EM → 30,000 capped → 60,000 KrisFlyer miles — the research doc's own worked number; 999 < min-transfer 1000 → 0). GREEN: `transfer_math.py` + `opportunities.py`, all passing, mypy strict clean. Two documented deviations from blueprint wording (fees not folded into rates; annual caps applied once for ≤12-month horizons) — decision log `2026-07-04-phase2-valuation-engine-math-contract.md`. The `backend-reviewer` re-derived every golden value by hand (all matched) and caught one real bug — `.normalize()` after `.quantize()` emits scientific notation (`1E+1`) for round-number rates, which would have hit JSONB/API payloads; fixed with a str()-based regression test, and DCB/Regalia/HSBC golden assertions added (73 tests total). Note for Phase 3's reviewer: confirm Simulation's monthly ledger is the cap-truth layer that corrects Stage 5's static blend. Next: Phase 3 Simulation Engine.

Earlier same day — **Build-plan Phase 1 (Knowledge Engine) done, test-first.** 29 failing tests written first (golden seed values, validate_catalog invariants, the flagship "Hyderabad→Singapore business, 8 months, 2 pax" resolution, buffer-rounds-up boundary); implementation passed on first green run. Seeds for all 8 cards written under a conservative + provenance-tagged policy — research-doc values golden-tested, market-knowledge values flagged `needs_verification: true` (the user's open review queue and the single biggest product risk). Key modeling call: **HDFC = two currencies** (Infinia/DCB tier 1:1 vs Regalia tier 2:1) instead of a premature card-override column. Seeds loaded into live Supabase; DB re-read hashes to the identical snapshot version (`cat-ee2d1c3701e4`). The `backend-reviewer` phase-exit pass confirmed every research-doc value exact and found 4 issues, all fixed same-day with regression tests (44 total): ambiguous program hints now clarify instead of silently picking KrisFlyer; catalog SELECTs gained ORDER BY id + order-independent round-trip check; version hash normalizes Decimals; duplicate (card, category) pairs fail validation loudly. Decision log: `2026-07-04-phase1-knowledge-engine-and-seed-catalog.md`. Also this session: tracker trimmed back to current-state-only per its own rules. Next: Phase 2 Valuation Engine.
