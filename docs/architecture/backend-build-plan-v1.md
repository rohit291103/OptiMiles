# OptiMiles — Backend & Database Build Plan v1

**Document Type:** Backend Architecture / Build Plan
**Version:** v1.0
**Status:** Active — the entry-point document for backend implementation. Start here.
**Date:** 2026-07-03

---

## 0. Assessment — are we building this right?

Honest verdict before committing to build: **yes, the architecture is sound and unusually well-prepared for a Phase-0 project.** What's right, and what to watch:

**What's right (keep doing):**
- **The deterministic-core / AI-edges split is the correct architecture for a trust product.** Every competitor failure mode this product exploits (generic advice, black-box AI, wrong calculations) is structurally prevented, not just discouraged. The docs enforce it consistently from Constitution → Scope → blueprint → engine specs.
- **The five-engine modular monolith is right-sized.** No microservices, no queues, no agent frameworks — plain Python modules a single developer can hold in their head, with clean seams for the two things that will actually change (ranking weights, allocation algorithm).
- **Scope discipline is real:** 8 cards, 2 airline programs, 3 routes, 6 screens. Small enough to hand-validate every reward rule — which is the entire moat.
- **Docs now agree with each other.** One vocabulary (Core Domain Model), one pipeline (execution blueprint v1.1), one scope (MVP Scope v2), reconciled 2026-07-03.

**Watchouts (the honest part):**
1. **Documentation is now ahead of code — this is the last planning doc.** 30+ docs, zero backend code. The next artifact merged into this repo should be `backend/pyproject.toml`, not another spec. Valuation and Simulation engine specs can be written as docstrings + tests, not standalone docs.
2. **The product risk is data, not code.** The engines are a few thousand lines of well-specified Python; the hard part is that `2:1 Infinia→KrisFlyer` is *actually correct today*. Treat seed data as the highest-review-bar artifact in the repo (§6).
3. **Greedy allocation vs. milestone/cap interactions** is the one place the "heuristic-first" bet could be wrong. Contained by design (simulation catches overstatement; OR-Tools escape hatch behind one interface) — but write adversarial test cases for it early.
4. **Don't let the RKE spec's full ambition leak into MVP scaffolding.** Merchants, promotions, scraping, full rule versioning are *post-MVP* (RKE spec §12.2). Build the schema below, not the whole Layer-2 vision.

---

## 1. Governing documents

This plan points; the documents below govern. If this doc and a governing doc conflict, the governing doc wins (and file a decision to fix the drift).

| Question | Governing doc |
|---|---|
| What are we building / for whom / how narrow? | [`prd/mvp-scope-v2.md`](../prd/mvp-scope-v2.md) (canonical scope) · [`prd/optimiles-constitution-v1.md`](../prd/optimiles-constitution-v1.md) (tie-breaker) |
| How does a request execute end-to-end? | [`system-execution-flow-v1.md`](system-execution-flow-v1.md) **v1.1 — the canonical pipeline** (11 stages, AI sandwich, ownership boundaries) |
| What do domain words mean? | [`core-domain-model-v1.md`](core-domain-model-v1.md) |
| Database tables | [`db-schema-v1.md`](db-schema-v1.md) **+ the v1.1 amendment in §3 below** (this plan is the v1.1 source of truth until the schema doc is bumped) |
| Knowledge Engine behavior | [`reward-knowledge-engine-spec-v1.md`](reward-knowledge-engine-spec-v1.md) (MVP subset per its §12.2) |
| Feasibility / generation / ranking rules | [`optimization-engine-spec-v1.md`](optimization-engine-spec-v1.md) (BR-01…07 generation, BR-01…06 ranking) |
| Product-level workflow + resolved design conflicts | [`recommendation-engine-design-v1.md`](recommendation-engine-design-v1.md) |
| What the API must feed (screens) | [`ux/goal-to-strategy-user-journey-v1.md`](../ux/goal-to-strategy-user-journey-v1.md) |
| Process (TDD, reviews, docs) | Root `CLAUDE.md` → "Backend Build Rules" |

---

## 2. Decisions locked by this plan

| # | Decision | Rationale |
|---|---|---|
| D-1 | **Reward Currency is a first-class entity; transfer relationships belong to currencies, not cards.** | RKE AD-04. HDFC Infinia/DCB/Regalia all earn HDFC Reward Points at one KrisFlyer ratio — per-card transfer rows store the same fact 3× and *will* drift. Chosen now because it changes the Knowledge Engine's core types and costs ~nothing pre-code, a painful migration later. |
| D-2 | **Lineage columns on results** (`catalog_snapshot_version`, `engine_version`) from day one. | Blueprint §9.6 — makes every historical recommendation reproducible/auditable. |
| D-3 | **PydanticAI for the two LLM calls; no LangGraph.** Provider (OpenAI/Gemini) behind one config setting inside `ai_reasoning/` only. | Blueprint §9.4 — a linear pipeline needs no graph framework; revisit only if the clarification loop grows real branching. |
| D-4 | **SQLAlchemy 2.x (async) + Alembic migrations** against Supabase Postgres; PgBouncer transaction mode per db-schema §6.5. RLS stays on user tables even though FastAPI uses the service role — defense in depth for any future direct-from-frontend reads. | Standard, boring, matches the schema doc. |
| D-5 | **Two-part response API** (structured results first, narration second) is the *planned* shape, not a later optimization. | Scope v2's 30s budget has no slack for a slow narration call; blueprint §8.3. |
| D-6 | **`uv` + `pytest` + `ruff` + `mypy (strict on engines)`**; every engine module DB-free and fixture-tested before the next begins. | TDD is mandatory for engine logic (CLAUDE.md trigger); DB-free engines are what make that cheap. |
| D-7 | **No OR-Tools/NetworkX in the MVP build.** Greedy allocation per blueprint Stage 7; OR-Tools only behind `generate_candidates()` when a real failing case demands it. | "Heuristic-first" (CLAUDE.md, PRD risk 8-B). The stack list is a menu, not an obligation. |

---

## 3. Database plan — Schema v1.1 amendment

`db-schema-v1.md` remains the base. Since **no migration has ever run**, these amendments are applied to the initial DDL (no data migration). When convenient, fold them into a `db-schema-v2.md`; until then this section is authoritative.

### 3.1 New table: `reward_currencies` (D-1)

```sql
CREATE TABLE reward_currencies (
  id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  currency_name  TEXT        NOT NULL UNIQUE,   -- 'HDFC Reward Points', 'EDGE Miles', 'EDGE Rewards', 'Membership Rewards', 'HSBC Reward Points', 'SBI Reward Points'
  issuer         TEXT        NOT NULL,          -- 'HDFC', 'Axis', 'Amex', 'HSBC', 'SBI'
  expiry_rules   TEXT,                          -- human-readable; structured later if engines need it
  is_active      BOOLEAN     NOT NULL DEFAULT TRUE,
  metadata       JSONB,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 3.2 Changed: `cards`

```sql
-- REPLACE:  points_currency TEXT NOT NULL
-- WITH:
reward_currency_id UUID NOT NULL REFERENCES reward_currencies(id)
```

### 3.3 Changed: transfer junction becomes currency-level

`card_transfer_partners` is **renamed and re-keyed** to `currency_transfer_partners`:

```sql
CREATE TABLE currency_transfer_partners (
  id                    UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
  currency_id           UUID    NOT NULL REFERENCES reward_currencies(id) ON DELETE CASCADE,
  partner_id            UUID    NOT NULL REFERENCES transfer_partners(id) ON DELETE CASCADE,
  ratio_from            INTEGER NOT NULL DEFAULT 1,
  ratio_to              INTEGER NOT NULL DEFAULT 1,
  min_transfer_points   INTEGER NOT NULL DEFAULT 1000,
  max_transfer_points   INTEGER,                -- NULL = uncapped (RKE spec models max; recent bank caps make this real)
  transfer_fee_inr      INTEGER NOT NULL DEFAULT 0,
  processing_days_min   INTEGER NOT NULL DEFAULT 1,
  processing_days_max   INTEGER NOT NULL DEFAULT 5,
  is_active             BOOLEAN NOT NULL DEFAULT TRUE,
  notes                 TEXT,
  CONSTRAINT uq_currency_partner UNIQUE (currency_id, partner_id)
);
```

**Card-level exceptions** (a bank granting one card a better ratio than the shared currency — rare, but Axis has done tier-based ratios): add a nullable `card_id UUID REFERENCES cards(id)` override column *only when the first real exception appears in validated data* — not speculatively. The eligibility rule "which cards can use this transfer link" is: card → currency → links.

### 3.4 Changed: lineage columns (D-2)

```sql
ALTER TABLE simulation_results      ADD COLUMN catalog_snapshot_version TEXT NOT NULL,
                                    ADD COLUMN engine_version           TEXT NOT NULL;
ALTER TABLE recommendation_outputs  ADD COLUMN catalog_snapshot_version TEXT,
                                    ADD COLUMN engine_version           TEXT;
```

`catalog_snapshot_version` (MVP) = max `updated_at` across catalog tables at snapshot load; `engine_version` = backend package version.

### 3.5 Migration dependency order (updated)

```
1. reward_currencies                       ← NEW, first
2. transfer_partners
3. cards                                   [→ reward_currencies]
4. reward_categories                       [→ cards]
5. currency_transfer_partners              [→ reward_currencies, transfer_partners]   ← replaces card_transfer_partners
6. reward_milestones                       [→ cards]
7. award_charts                            [→ transfer_partners]
8–14. user/simulation/recommendation layers unchanged from db-schema-v1 (+ §3.4 columns)
```

Everything else in `db-schema-v1.md` (indexes, RLS, cascade rules, JSONB decisions) stands, with the junction-table indexes re-pointed at `currency_transfer_partners(currency_id, partner_id)`.

---

## 4. Backend repository layout

```
backend/
  pyproject.toml                # uv-managed; ruff + mypy + pytest config
  alembic/                      # migrations (initial DDL = db-schema-v1 + §3 amendment)
  app/
    domain/                     # shared kernel: Pydantic models ONLY, no I/O
    knowledge/                  # Engine 1 — sole reader of catalog tables
    valuation/                  # Engine 2 — pure; incl. opportunities.py
    simulation/                 # Engine 4 — pure; projector.py
    optimization/               # Engine 3 — pure; feasibility / strategies / ranking
    ai_reasoning/               # Engine 5 — only module with an LLM client
    pipeline/                   # orchestrator: context.py, run.py, assemble.py
    repositories/               # user-layer reads + ALL writes (orchestrator-owned)
    api/                        # FastAPI routers + response schemas
    config.py                   # pipeline_settings, ranking weights path, LLM provider
  seeds/                        # catalog data as reviewed YAML/JSON + loader
  tests/                        # unit/<engine>/, fixtures/, integration/
```

Rules baked into this layout (from blueprint §3, §7): engines never import each other except Valuation's pure math; `domain/` imports nothing; only `knowledge/` + `repositories/` touch the DB; only `ai_reasoning/` touches an LLM.

---

## 5. Build phases

Sequential; each phase's exit criteria gate the next. TDD (red-green-refactor) for every calculation path.

| Phase | Deliverable | Exit criteria |
|---|---|---|
| **0. Skeleton** | FastAPI app boots; `domain/` types for all pipeline objects (blueprint §4 table); Alembic initial migration (§3); CI (ruff, mypy, pytest) | `GET /health` 200; migration applies clean to a fresh Supabase project |
| **1. Knowledge** | Catalog models + snapshot loader + `validate_catalog()` invariants + **seed data for all 8 cards** (§6); goal resolution + requirement estimation (Stages 2–3) | Seeds pass validation in CI; snapshot loads; award-chart lookups fixture-tested; unsupported routes rejected explicitly |
| **2. Valuation** | Pure transfer/earn math + `opportunities.py` enumeration (Stage 5) | Effective miles-per-₹100 correct against hand-computed fixtures for every (card, category, KrisFlyer) path; SBI Cashback yields zero KrisFlyer opportunities |
| **3. Simulation** | `projector.py` monthly ledger (Stage 8) | Cap boundaries, milestone triggers, transfer processing delays, starting balances all fixture-tested; pure function (no DB) |
| **4. Optimization** | `feasibility.py` (+ `PortfolioAssessment`, adjustment options), `strategies.py` (archetypes + BR validation), `ranking.py` (prune → hard rules → preference-weighted score from config) | Adversarial milestone/cap allocation cases pass (watchout #3); infeasible goals return adjustment options; near-tie prefers simpler; every ranked output carries a score breakdown |
| **5. AI Reasoning** | `extract_intent()` + `narrate()` via PydanticAI; number-echo validation; **template fallback in the same PR** | Both functions mocked-LLM tested; fallback produces a complete narration with the LLM disabled; out-of-vocabulary output becomes clarification, never passthrough |
| **6. Pipeline + API** | `pipeline/run.py` composing Stages 1–11; persistence with lineage; API v1 (§7) | End-to-end: goal text → full Recommendation Package against seeded catalog; replaying the same inputs + snapshot version is byte-identical (determinism test); p95 deterministic core < 1s |
| **7. Integration** | Wire the landing-page Goal Simulator to `POST /simulations` (replacing the static mock); auth wiring for saved goals | Simulator returns real engine numbers; `verify`-style end-to-end pass in the browser |

Each phase ends with: `backend-reviewer` agent pass, tracker refresh, decision log if anything deviated from plan.

---

## 6. Seed data — the highest-review-bar artifact

- Seeds live in `backend/seeds/` as human-reviewable YAML, loaded by script — catalog is **config, not code** (Scope v2 NFR).
- Every reward rule, ratio, cap, milestone and award-chart row carries a `source` field (bank T&C URL / research doc reference) and a `verified_on` date. Primary basis: [`research/singapore_airlines_krisflyer_indian_credit_card_research_v1.md`](../research/singapore_airlines_krisflyer_indian_credit_card_research_v1.md) — **re-verify against current bank pages at seed time; the research doc is a starting point, not truth.**
- `validate_catalog()` (runs on snapshot load + in CI): every card has a currency, a `default` reward category, ≥1 active category; every currency claiming KrisFlyer reach has an active transfer link; ratios within sane bounds (1:4 … 5:1); award chart covers the 3 MVP routes × business; no orphan FKs; SBI Cashback has **no** transfer links (it's the deliberate negative case).
- A wrong ratio shipped confidently is the product's existential failure (PRD risk 8-A) — seed PRs get human review line-by-line.

---

## 7. API surface v1 (deliberately small)

| Endpoint | Purpose | Pipeline |
|---|---|---|
| `POST /goals/parse` | NL text → `ParsedGoalIntent` \| `ClarificationRequest` (client holds loop state) | Stage 1 |
| `POST /goals` | Validated intent → persisted goal + `RewardRequirement` | Stages 2–3 |
| `POST /goals/{id}/recommendation` | Full run → **structured Recommendation Package** (narration streamed/polled second, D-5) | Stages 4–11 |
| `POST /simulations` | Spend profile (+ optional pins) → simulation result; also serves the public landing simulator (rate-limited, anonymous allowed) | Stages 4, 5, 8 |
| `GET /catalog/cards` | Supported cards for pickers | snapshot read |
| `GET /health` | liveness + catalog snapshot version | — |

---

## 8. Definition of done (MVP backend)

A user (or the frontend simulator) can: submit "Singapore Airlines business class from Hyderabad in 8 months" → get goal validation, a 70k+buffer KrisFlyer requirement from the seeded award chart, a feasibility verdict with portfolio assessment, 1–4 ranked strategies with month-by-month projections and score breakdowns, and a narration (LLM or template) in which **every number traces to a deterministic artifact** — inside 30 seconds, reproducibly.

**Non-goals (do not build, per Scope v2):** merchants/promotions/portals data, scraping infrastructure, rule versioning beyond lineage columns, OR-Tools, LangGraph, hotel/lounge surfacing, award availability, multi-goal optimization, queues/workers/events.

---

*Maintained by: OptiMiles Backend Team. v1.0 (2026-07-03) — initial build plan; locks D-1…D-7. Next review: end of Phase 1 (Knowledge Engine + seeds), or on any deviation from the phase exit criteria.*
