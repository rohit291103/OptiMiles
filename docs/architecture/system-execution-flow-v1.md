# OptiMILES — System Execution Flow v1

**Document Type:** System Architecture Specification
**Document Category:** 02 Business Architecture
**Version:** 1.1.0
**Status:** Canonical execution blueprint (Phase 0)
**Depends on:** `docs/prd/mvp-scope-v2.md`, `docs/architecture/db-schema-v1.md`, root `CLAUDE.md` (Core Backend Systems)
**Related specs:** [recommendation-engine-design-v1.md](recommendation-engine-design-v1.md) (product-level workflow + reconciliation), [optimization-engine-spec-v1.md](optimization-engine-spec-v1.md), [reward-knowledge-engine-spec-v1.md](reward-knowledge-engine-spec-v1.md), [core-domain-model-v1.md](core-domain-model-v1.md), [reward-opportunity-engine-design-v1.md](reward-opportunity-engine-design-v1.md), [strategy-ranking-engine-design-v1.md](strategy-ranking-engine-design-v1.md), [simulation-engine-spec-v1.md](simulation-engine-spec-v1.md)

> **v1.1 (2026-07-03):** reconciled against the Notion engine docs (RED/REW/RIF, SGE, SRE, RKE, CDM), now mirrored into this repo. Adopted: preference-aware ranking weights (DP-07), explicit strategy validation + pruning steps, `PortfolioAssessment` as a named Stage-6 output, the Recommendation Package payload contract, portfolio-utilization ranking dimension, and the tightened **30-second** performance target from MVP Scope v2. Conflicts resolved (AI-assisted generation → deterministic; "every feasible strategy" → bounded archetypes) are recorded in recommendation-engine-design-v1.md §6.2.

---

## Table of Contents

1. [High-Level System Execution Flow](#1-high-level-system-execution-flow)
2. [Detailed Stage-by-Stage Execution](#2-detailed-stage-by-stage-execution)
3. [Engine Interaction Diagram](#3-engine-interaction-diagram)
4. [Data Flow](#4-data-flow)
5. [Responsibility Matrix](#5-responsibility-matrix)
6. [Sequence Diagram](#6-sequence-diagram)
7. [Dependency Graph](#7-dependency-graph)
8. [Design Review](#8-design-review)
9. [Recommendations](#9-recommendations)

---

## 0. Architectural Stance (read first)

Three decisions shape everything below. They are stated here so every stage description can assume them.

### 0.1 The "AI sandwich"

The pipeline is deterministic in the middle and AI-assisted only at the two edges:

- **Entry edge:** the LLM converts messy human language into a structured, validated goal (and asks clarifying questions when it can't).
- **Exit edge:** the LLM converts structured, already-computed results into a human explanation.
- **Everything in between** — eligibility, valuation, allocation, simulation, ranking — is deterministic code over catalog data. The LLM never sees this middle section, never produces a number, and never picks a winner.

This is the mechanical enforcement of the Engineering Philosophy in root `CLAUDE.md` ("structured systems first, AI orchestration second") and the direct mitigation for MVP Risk 8-C (hallucinated recommendations).

### 0.2 Orchestration is code, not an LLM

Root `CLAUDE.md` lists "orchestration" among LLM responsibilities. For the *execution pipeline* this document deliberately narrows that: the pipeline is a plain, linear Python function in the FastAPI app that calls engines in order. There is no LLM (and no LangGraph graph) deciding which engine runs next — the flow is identical for every request, so routing intelligence would be complexity with no decision to make.

The LLM's "orchestration" role is confined to the **conversational edge**: deciding whether the user's input is complete enough to start the pipeline, and asking clarification questions if not. That is the only place a branch depends on language understanding. (LangGraph, if used at all, lives only there — see §8.4.)

### 0.3 The five engines are the module boundary

The engine design docs (originally Notion; now mirrored — `Reward Opportunity Engine` in RKE-001 AD-05, `Strategy_Generation_Engine_Design_v1`, `Strategy Ranking Engine Design`) name a "Reward Opportunity Engine," "Strategy Engine," and "Ranking Engine." This document maps them onto the five backend systems already defined in root `CLAUDE.md`, rather than promoting them to peer engines:

| Working name (in design docs) | Canonical home | Why |
|---|---|---|
| Reward Opportunity Engine | **Reward Valuation Engine** — its enumeration API (`enumerate_opportunities`) | "What earning/transfer paths exist and what is each worth" is valuation work. Splitting enumeration from per-path valuation would create two shallow modules that always change together. |
| Strategy (Generation) Engine | **Optimization Engine** | Composing opportunities into candidate strategies under constraints *is* the optimization job CLAUDE.md assigns ("spend allocation, card strategy generation"). Same engine, clearer description. |
| Ranking Engine | **Optimization Engine** — a pure scoring module (`ranking.py`) | Ranking is a weighted scoring function over simulation results (~a page of code plus a weights config). As a standalone engine its interface would be as complicated as its implementation — the definition of a shallow module. |

Section 9 records this as a formal recommendation for the in-flight engine specs.

---

## 1. High-Level System Execution Flow

Two request families share the engines but have different entry points:

- **Flow A — Goal → Recommendation** (the core product flow, this document's spine)
- **Flow B — Simulation replay** (user tweaks spend assumptions on an existing goal; re-enters the pipeline at Stage 4)

```
                         FLOW A: GOAL → RECOMMENDATION

  User goal (free text or structured form)
        │
        ▼
  [ 1] Intent Extraction & Clarification .............. AI-assisted
        │            ▲
        │            └── clarification loop with user (0..N turns)
        ▼
  [ 2] Goal Resolution & Validation .................... deterministic
        ▼
  [ 3] Reward Requirement Estimation ................... deterministic
        ▼
  [ 4] Planning Context Assembly ....................... deterministic   ◄── FLOW B re-entry
        ▼
  [ 5] Opportunity Enumeration & Valuation ............. deterministic
        ▼
  [ 6] Feasibility Gate ................................ deterministic
        │  (infeasible → short-circuit to Stage 10 with adjustment options)
        ▼
  [ 7] Candidate Strategy Generation ................... deterministic
        ▼
  [ 8] Timeline Simulation (per candidate) ............. deterministic
        ▼
  [ 9] Ranking & Selection ............................. deterministic
        ▼
  [10] Explanation & Narration ......................... AI-assisted
        ▼
  [11] Recommendation Assembly & Persistence ........... deterministic
        ▼
  Final Recommendation (structured payload + narration)
```

Properties of this shape:

- **Stages 2–9 and 11 are pure or DB-only.** Given the same goal, the same user context, and the same catalog snapshot, they produce byte-identical results. This is what makes recommendations auditable and testable.
- **Only Stages 1 and 10 call an LLM** — at most two LLM round-trips per request (plus clarification turns, which are user-paced and outside the compute budget).
- **One synchronous request.** MVP Scope v2 targets a trustworthy strategy in **30 seconds** (v1 allowed 30–60s); the deterministic core runs in milliseconds-to-seconds, LLM calls dominate. No queues, no workers, no events — a single FastAPI request handles the whole pipeline (§8.3 sizes this claim; response streaming is the lever if the tightened budget is threatened).
- **Failure degrades downward, never sideways.** A narration failure falls back to template text over the same structured facts; an optimizer edge case falls back to the "status quo wallet" baseline strategy; an unsupported route fails explicitly. No stage ever guesses.

---

## 2. Detailed Stage-by-Stage Execution

Conventions used below:
- *Deterministic* = same inputs → same outputs, no LLM, unit-testable with fixtures.
- *Catalog snapshot* = the versioned, in-memory read model of catalog tables served by the Knowledge Engine (§3.2). Every stage that touches reward data receives the **same** snapshot reference; a request never mixes two catalog states.

---

### Stage 1 — Intent Extraction & Clarification

**Purpose.** Convert free-form user language ("I want to fly Singapore Airlines business class from Hyderabad in 8 months") into a machine-checkable `ParsedGoalIntent`, or determine that the input is incomplete and ask exactly what's missing.

**Business problem.** Users think in trips, not in award-chart coordinates. Forcing a structured form on first contact kills the "AI strategist" experience; letting the LLM's reading of the sentence flow unchecked into calculations kills trust. This stage buys the natural-language entry without paying the hallucination cost, because its output is *only a proposal* — Stage 2 validates every field against the catalog.

**Inputs.** Raw goal text; user profile basics (home city default from `users.city`); the *vocabulary lists* of supported destinations/programs/cabins (names only, so the LLM can normalize "biz class to SG" — not ratios, not miles, not prices).

**Outputs.** `ParsedGoalIntent` — a Pydantic-validated structure: `{origin_city?, destination_city?, cabin_class?, program_hint?, timeline_months?, num_passengers?, missing_fields[], confidence}` — **or** a `ClarificationRequest` (one focused question per missing/ambiguous field).

**Internal responsibilities.**
- Single constrained LLM call with structured output (Pydantic schema enforcement via PydanticAI).
- Normalize synonyms to canonical slugs ("SQ", "SIA", "Singapore Air" → `singapore-airlines`).
- Emit `missing_fields` honestly rather than inventing defaults; the only permitted default is origin city from the user profile (flagged as `assumed`).
- Loop: clarification answers re-enter this stage with accumulated context until `missing_fields` is empty or the user abandons.

**Dependencies.** AI Reasoning Layer (owner). Knowledge Engine (read-only vocabulary lists). No writes.

**Data required.** Supported destination/program/cabin vocabulary from the catalog snapshot.

**Failure scenarios.**
- LLM unavailable/timeout → fall back to the structured form UI (the frontend always has one; NL entry is an enhancement, not the only door).
- LLM returns out-of-vocabulary values → treated as `missing_fields`, triggers clarification — never passed downstream.
- User asks for something out of MVP scope ("optimize my taxes") → scope-refusal template response; pipeline never starts.

**AI vs deterministic.** AI-assisted (one of only two AI stages). The schema validation of its output is deterministic.

**Why this stage is first.** Nothing downstream can run on ambiguous input, and clarification is cheapest before any compute is spent. It cannot merge with Stage 2: parsing (linguistic, probabilistic) and validation (catalog lookup, exact) have different failure modes and different owners, and keeping them separate is what makes the LLM's output safely discardable.

---

### Stage 2 — Goal Resolution & Validation

**Purpose.** Turn the `ParsedGoalIntent` proposal into a validated, persisted `TravelGoal` (`user_goals` row) whose every field is confirmed against catalog reality.

**Business problem.** This is the trust boundary. Past this line, every value in the system is either user-confirmed or catalog-derived — nothing downstream ever needs to wonder whether a field was hallucinated.

**Inputs.** `ParsedGoalIntent`; catalog snapshot; user id.

**Outputs.** `TravelGoal` — persisted `user_goals` row with `partner_id`, `award_chart_id` (snapshot-locked, per db-schema-v1), `origin_city`, `destination_city`, `cabin_class`, `num_passengers`, `target_date`, `status='active'`.

**Internal responsibilities.**
- Map cities to award-chart regions (Hyderabad → India; Singapore → Southeast Asia) via a small deterministic mapping table.
- Verify the (partner, origin region, destination region, cabin, award type) tuple has an active `award_charts` row — this is the "supported route" check.
- Convert relative timeline ("in 8 months") to an absolute `target_date`.
- Lock `award_chart_id` so later chart updates don't silently move this goal's target (already a schema-level decision).
- Persist and return the canonical goal.

**Dependencies.** Knowledge Engine (award chart lookup); Database (write `user_goals`).

**Data required.** `award_charts`, `transfer_partners`, region-mapping table.

**Failure scenarios.**
- No award chart row → explicit `UnsupportedRoute` result with the list of supported routes. **Never** estimate an unsupported route.
- Ambiguous region mapping (city not in mapping table) → back to Stage 1 clarification.
- Target date in the past / passengers ≤ 0 → validation error to user.

**AI vs deterministic.** Fully deterministic.

**Why here.** Validation must precede any estimation; persisting the goal here (not at the end) means an abandoned or failed pipeline run still leaves the user's goal saved and resumable.

---

### Stage 3 — Reward Requirement Estimation

**Purpose.** Compute *what winning looks like*: the total miles target and expected cash component for this goal.

**Business problem.** Every downstream judgment — feasibility, strategy ranking, "months to goal" — needs a fixed numeric target. Getting this number from the award chart (not from an LLM, not from heuristics) is the product's core honesty guarantee.

**Inputs.** `TravelGoal` (with locked `award_chart_id`); catalog snapshot.

**Outputs.** `RewardRequirement` — `{target_program, miles_required_total (= chart miles × passengers), taxes_fees_inr_estimate, award_type, one_way_or_return, buffer_miles}`.

**Internal responsibilities.**
- Award chart lookup and passenger multiplication (denormalized back onto `user_goals.target_miles`).
- Apply a configurable safety buffer (e.g. +5%) for devaluation/availability risk — explicitly surfaced in the explanation later, never hidden.
- Attach the taxes/fees estimate so the recommendation can state the full redemption cost.

**Dependencies.** Knowledge Engine only.

**Data required.** `award_charts` row (already locked by Stage 2).

**Failure scenarios.** Chart row deactivated between goal creation and a later re-run → requirement recomputed against the locked snapshot row, with a `stale_chart` warning attached for the explanation stage. This is a warning, not an error — the locked reference is authoritative for this goal by design.

**AI vs deterministic.** Fully deterministic.

**Why a separate stage from 2.** Validation answers "is this goal expressible?"; estimation answers "what does it cost?". Flow B (simulation replay) and future goal-editing flows re-run estimation without re-running resolution, and the split keeps the trust boundary (Stage 2) free of arithmetic.

---

### Stage 4 — Planning Context Assembly

**Purpose.** Gather *everything the deterministic core will be allowed to know* into one immutable `PlanningContext` object.

**Business problem.** Engines that individually query the database produce recommendations that are impossible to reproduce ("which catalog state was this computed against?"). One assembly point makes every run reproducible, testable with fixtures, and auditable.

**Inputs.** `TravelGoal` + `RewardRequirement`; user id; optional simulation overrides (Flow B: edited spend profile, pinned card assignments from `simulation_line_items`).

**Outputs.** `PlanningContext` — frozen structure containing:
- catalog snapshot reference (cards, reward categories, milestones, transfer links, all filtered `is_active`),
- user wallet (`user_cards` with balances),
- spend profile (monthly spend by category — user-declared, from simulation line items or onboarding),
- the goal and requirement,
- planning horizon (months until `target_date`),
- constraint set (pinned card assignments, "no new cards" toggle, max annual fees tolerance — MVP keeps this list tiny).

**Internal responsibilities.**
- Load user state from the DB (the only user-data read in the core).
- Resolve the catalog snapshot version for this request and pin it.
- Normalize the spend profile onto canonical `category_slug` values.
- Apply defaults where the user gave none (e.g., default spend profile template) — every default flagged `assumed: true` so the narration can say "based on a typical ₹X/month profile — adjust it for a sharper plan."

**Dependencies.** Knowledge Engine (catalog snapshot); Database (user layer reads).

**Data required.** `user_cards`, `user_goals`, `spend_simulations` + `simulation_line_items` (Flow B), full catalog layer.

**Failure scenarios.**
- User has no cards and allows no new cards → context still assembles; Stage 6 will declare infeasibility with the obvious fix.
- Spend profile absent → default template applied and flagged; never silently zero.

**AI vs deterministic.** Fully deterministic.

**Why here.** This is Flow B's re-entry point: a simulation tweak is just a new `PlanningContext` over the same goal. Placing assembly after requirement estimation means replays skip Stages 1–3 entirely.

---

### Stage 5 — Opportunity Enumeration & Valuation

**Purpose.** Enumerate every *individually sensible* way to earn toward the target program, and price each one in a common currency: **effective target-program miles per ₹100 spent**.

**Business problem.** Strategy generation is a search problem; this stage builds the search space with honest per-edge economics. It answers, per (card, category, transfer path): "if ₹100 goes here, how many KrisFlyer miles eventually come out, after ratios, caps, fees and delays?"

**Inputs.** `PlanningContext`.

**Outputs.** `OpportunitySet` — list of `RewardOpportunity`:
`{card_id, in_wallet: bool, category_slug, earn_rate, cap_structure, transfer_path: {partner_id, ratio_from:ratio_to, min_transfer, fee_inr, processing_days}, effective_miles_per_100inr, valuation_notes[]}`
plus per-card aggregates (milestone schedule, annual fee, welcome bonus if `in_wallet=false`).

**Internal responsibilities (this is the "Reward Opportunity Engine" work, homed in the Valuation Engine).**
- **Eligibility filter:** only cards with an active transfer link to the goal's program (directly, or — MVP: direct only) produce opportunities; SBI Cashback correctly produces none for a KrisFlyer goal.
- **Path valuation:** earn rate × transfer ratio → effective miles per ₹100, degraded by caps (marginal rate after cap = base rate) and amortized fees.
- **Both wallets:** enumerate for cards the user holds *and* the 8-card MVP universe (candidate acquisitions), tagged `in_wallet`.
- Record `valuation_notes` (cap applies, exclusion applies, ratio worse than headline) — raw material for explainability.

**Dependencies.** Reward Valuation Engine (owner); consumes only the `PlanningContext` (no DB, no Knowledge Engine calls — everything needed is in the snapshot).

**Data required.** Catalog snapshot: `reward_categories`, `card_transfer_partners`, `reward_milestones`, `cards`.

**Failure scenarios.**
- Empty `OpportunitySet` (no card in the universe reaches the program) → flows to Stage 6, which declares structural infeasibility.
- Data inconsistency (card with transfer link but no reward categories) → hard error with catalog-data alert; bad reference data must fail loudly, not produce silent zeros.

**AI vs deterministic.** Fully deterministic. Pure function of `PlanningContext`.

**Why before strategy generation.** Valuing paths independently of strategies means each path is priced exactly once, strategies become cheap combinations, and every number in a final recommendation traces back to a named opportunity — the unit of explainability.

---

### Stage 6 — Feasibility Gate

**Purpose.** Decide *before* generating strategies whether the goal is achievable within the horizon, and if not, compute which adjustments would make it achievable.

**Business problem.** An impossible goal answered with a strategy list is a lie; answered with "not in 8 months as stated — but yes with one of these three changes" it is the most trust-building screen in the product. This also short-circuits wasted compute and prevents the ranking stage from dressing up the least-bad infeasible plan as a recommendation.

**Inputs.** `OpportunitySet`, `RewardRequirement`, `PlanningContext`.

**Outputs.** `FeasibilityVerdict` — `{feasible: bool, best_case_miles, gap, adjustment_options[]}` where adjustments are computed variants: extend timeline to N months / add card X / raise category-Y spend by ₹Z / switch to premium economy. *(v1.1)* Also emits `PortfolioAssessment` — `{current_capability, convertible_balances_by_program, reward_gap, strengths[]}` — the "Current Portfolio Assessment / Reward Gap Analysis" sections of the Recommendation Package and the dashboard's achievability hero.

**Internal responsibilities.**
- Upper-bound check: route all spend to the best opportunity per category, add current balances (converted at actual ratios), milestones and welcome bonuses → `best_case_miles`. If `best_case_miles < miles_required`, infeasible.
- For infeasible goals, solve the inverse problems (smallest timeline extension; single best card addition; cabin downgrade) to produce concrete `adjustment_options`.
- On infeasible: skip Stages 7–9, jump to Stage 10 with the verdict — the "recommendation" becomes the adjustment menu.

**Dependencies.** Optimization Engine (owner — it's a bound computation over the same structures strategy generation uses).

**Data required.** None beyond inputs.

**Failure scenarios.** Borderline feasibility (gap < buffer) → feasible-with-warning; the narration must present it as tight, not certain.

**AI vs deterministic.** Fully deterministic.

**Why a dedicated stage.** Folding this into ranking ("all candidates score terribly") detects infeasibility *after* paying for generation and simulation, and can't produce principled adjustment options. The gate is cheap (one bound per category) and changes the product experience qualitatively.

---

### Stage 7 — Candidate Strategy Generation

**Purpose.** Compose opportunities into a small set of complete, executable `CandidateStrategy` objects, each with a full spend allocation.

**Business problem.** Users don't act on "opportunities"; they act on a plan: *which cards, which spend goes where, when to transfer*. Generating several structurally different candidates (rather than one "optimal" answer) is what lets the product show trade-offs — and showing trade-offs is an explainability feature, not a luxury.

**Inputs.** `OpportunitySet`, `PlanningContext`, `FeasibilityVerdict` (feasible only).

**Outputs.** `CandidateStrategy[]` (bounded: 3–8 candidates), each:
`{strategy_archetype, cards_used[] (+ cards_to_acquire[]), spend_allocation: {category_slug → card_id}, transfer_plan: [{from_card, to_program, points, planned_month}], expected_milestones[], assumptions[]}`

**Internal responsibilities (heuristic-first, per CLAUDE.md).**
- Generate candidates from **archetypes**, not exhaustive search:
  1. *Status quo optimized* — current wallet, spend re-routed optimally (always generated; it's also the baseline every other candidate is compared against).
  2. *One new card* — best single acquisition on top of the wallet (one candidate per justifiable card, capped).
  3. *Concentrated* — push spend toward milestone thresholds where the bonus beats spread-out earning.
  4. *Simplest viable* — fewest cards/actions that still clears the goal; some users pay miles for simplicity.
- Within each archetype, allocation is greedy: per category, route to the highest `effective_miles_per_100inr` opportunity, respecting caps (marginal-rate aware) and user pins from `simulation_line_items.assigned_card_id`.
- Milestone chasing as a greedy post-pass: divert spend to cross a threshold only if bonus miles > diverted-spend loss. (This is the known weak spot of greedy allocation; OR-Tools is the *later* answer if real cases prove it wrong — see §8.5.)
- Transfer plan: batch transfers respecting `min_transfer_points`, scheduled so processing delays land before `target_date`.
- Every candidate records its `assumptions[]` — the explanation stage narrates from these.
- *(v1.1)* **Explicit validation pass at exit** (business rules BR-01…BR-07 in [optimization-engine-spec-v1.md](optimization-engine-spec-v1.md) §2.5): eligibility, user-constraint compliance, transfer-path validity, completeness (partial strategies are invalid outputs). Validation failures discard the candidate, never patch it silently.

**Dependencies.** Optimization Engine (owner); Valuation Engine (pure re-valuation calls when allocation shifts a card across a cap boundary).

**Data required.** None beyond inputs.

**Failure scenarios.**
- Archetypes collapse to duplicates (tiny wallet) → deduplicate; 1–2 candidates is a valid outcome.
- Greedy allocation violates a cap interaction → assertion + fallback to base-rate allocation for that category (never emit an allocation that overstates earnings).

**AI vs deterministic.** Fully deterministic. **No LLM proposes, adjusts, or vetoes strategies.**

**Why archetypes.** The real search space (8 cards × 8 categories × milestones × transfer timing) is combinatorially large, but users can only compare ~3 plans. Archetypes make candidates *explainably different* ("this one is fastest; this one is simplest; this one avoids a new card") instead of numerically-adjacent siblings — which is exactly what the ranking and explanation stages need.

---

### Stage 8 — Timeline Simulation

**Purpose.** Project each candidate month-by-month from today to the target date: points earned, caps hit, milestones triggered, transfers executed, miles landed.

**Business problem.** A strategy is a claim about the future; the simulation is the receipt. "Month 6: you cross ₹8L on Infinia, +10,000 bonus points" is what turns a recommendation into a plan the user can follow and verify. It also catches *time-dependent* failures (monthly caps, transfer processing windows, points expiry later) that per-path valuation mathematically cannot see.

**Inputs.** One `CandidateStrategy` + `PlanningContext` (called once per candidate).

**Outputs.** `SimulationResult` per candidate — month-indexed ledger `{month → points_by_card, cap_utilization, milestones_triggered, transfers_executed, cumulative_target_miles}`, plus aggregates: `months_to_goal`, `miles_at_target_date`, `total_fees_inr`, `buffer_achieved`. Persisted to `simulation_results` (aggregates as columns, ledger in `card_allocations`/`milestone_projections` JSONB, per db-schema-v1).

**Internal responsibilities.**
- Discrete monthly ticks; within a month: spend → earn (cap-aware) → milestone checks → scheduled transfers (ratio, fee, `processing_days` shifting arrival).
- Start from `user_cards.current_points_balance`.
- Pure function: `simulate(strategy, context) → result`. No DB access during computation; persistence is the orchestrator's job afterward.

**Dependencies.** Simulation Engine (owner); Valuation Engine (same transfer-math pure functions — ratio conversion lives in exactly one place).

**Data required.** None beyond inputs (all reward rules ride in via the snapshot inside `PlanningContext`).

**Failure scenarios.**
- Simulated total ≠ strategy's claimed total beyond tolerance → the **simulation wins** (it models time; the generator doesn't); the candidate is re-labeled with simulated numbers, and a large gap flags a generator bug in logs.
- Candidate misses the goal in simulation despite passing the gate (cap timing effects) → candidate marked `misses_goal`, kept for ranking transparency but never rank #1.

**AI vs deterministic.** Fully deterministic.

**Why after generation, before ranking.** Ranking must score *simulated* outcomes, not generator estimates — otherwise ranking inherits the generator's optimism. And the same engine, called standalone with a user-edited context, *is* Flow B and the public simulator: one implementation, three consumers.

---

### Stage 9 — Ranking & Selection

**Purpose.** Order candidates by a transparent, explainable score and select the primary recommendation plus alternatives.

**Business problem.** "Best" is multi-dimensional (fastest vs. cheapest vs. simplest). The product must commit to a defensible default ordering *and* expose why, or the recommendation reads as arbitrary.

**Inputs.** `CandidateStrategy[]` + matching `SimulationResult[]`, `RewardRequirement`, `PlanningContext`.

**Outputs.** `RankedStrategy[]` — each `{strategy, simulation, score, score_breakdown: {goal_achievement, efficiency, cost, simplicity, risk}, rank, headline_differentiator}`.

**Internal responsibilities.**
- *(v1.1)* **Prune first:** remove duplicate and dominated strategies (worse or equal on every dimension than another candidate) before scoring — SRE workflow step 1.
- Weighted composite over named sub-scores:
  - *goal achievement* (dominant: reaches target by date, buffer size),
  - *efficiency* (miles per ₹ of routed spend),
  - *cost* (annual + transfer fees vs. redemption value),
  - *simplicity* (number of cards/actions/new applications),
  - *portfolio utilization* (*v1.1*, SRE dimension: preference for extracting value from cards the user already holds — the scoring teeth behind "Maximize Existing Cards First"),
  - *risk* (dependence on tight caps, single milestone, long transfer chains).
- Weights in a versioned config (not code) — the score maps to `simulation_results.optimization_score` and the LLM's stored `confidence_score` derives from it, never from LLM self-assessment.
- *(v1.1)* **Preference-aware weighting (DP-07):** the user's preference profile (annual-fee tolerance, timeline urgency, complexity tolerance, willingness to apply for new cards — collected in the UX Goal Discovery flow) deterministically modulates the dimension weights. Hard constraints (BR-03: "no new cards", max fee) filter *before* scoring; preferences tilt weights, they never override constraints.
- Tag each ranked strategy's `headline_differentiator` ("fastest", "no new cards", "lowest fees") — deterministic input for narration.
- Hard rules before weights: `misses_goal` candidates rank below all achieving ones, regardless of scores.

**Dependencies.** Optimization Engine (owner — `ranking.py` module, per §0.3).

**Data required.** Scoring weights config.

**Failure scenarios.** Near-tie at the top (Δscore < threshold) → both presented as co-recommendations; the narration says "genuinely close — hinges on whether you'll get a new card," which is more honest than a manufactured winner.

**AI vs deterministic.** Fully deterministic. **The LLM never reorders, vetoes, or blesses the ranking.**

**Why a stage of its own (but not an engine of its own).** Scoring deserves an isolated, unit-tested, config-driven module because its weights are the most-tuned artifact in the system — but its interface (`rank(candidates) → ranked`) is one function. Module: yes. Engine: no.

---

### Stage 10 — Explanation & Narration

**Purpose.** Convert the ranked, structured results into the explanation layer the PRD calls the core differentiator: why these cards, why this routing, why this beats the alternative, what to do first.

**Business problem.** Deterministic outputs are trustworthy but unreadable (JSON ledgers, score vectors). The narration makes them *legible* without making them *less true*.

**Inputs.** Top `RankedStrategy` + alternatives (score breakdowns, differentiators, assumptions, simulation aggregates, feasibility warnings, `valuation_notes`) — or, on the infeasible path, the `FeasibilityVerdict` with adjustment options.

**Outputs.** `RecommendationNarration` — `{summary (1–2 sentences), reasoning (structured prose), action_items[] (priority-ordered, each mapped to a strategy element), comparison_notes}` → persisted as `recommendation_outputs` rows with `model_version`.

**Internal responsibilities.**
- One LLM call. The prompt contains **only** the structured results — the LLM has no catalog access, no retrieval, no tools; it cannot introduce facts because it was never given any facts to distort, only facts to phrase.
- **Post-generation validation (deterministic):** extract every number and card/program name in the narration and verify each exists in the input payload. Any unmatched figure → one regeneration, then fallback.
- **Fallback:** template-based narration assembled from `score_breakdown` + `headline_differentiator` + `assumptions` ("Ranked #1 because it reaches 92,000 miles by March — 2 months ahead of target — using only cards you hold."). Stilted but true. **The numbers ship regardless of LLM availability; only eloquence degrades.**

**Dependencies.** AI Reasoning Layer (owner); Database (write `recommendation_outputs`).

**Data required.** None beyond inputs — by design.

**Failure scenarios.** LLM timeout/refusal/validation failure → fallback templates (above). Persist with `model_version='template-fallback'` for auditability.

**AI vs deterministic.** AI-assisted narration wrapped in deterministic validation.

**Why last-but-one.** Explanation over anything not-yet-final would need regeneration; and keeping it after ranking guarantees narration can *reference* the ranking rather than influence it.

---

### Stage 11 — Recommendation Assembly & Persistence

**Purpose.** Assemble the API response and finalize all persistence in one place.

**Business problem.** The frontend needs one coherent payload (strategies + simulations + narration + metadata); auditability needs the intermediate artifacts stored with lineage (`goal → simulation → result → recommendation`, matching the schema's FK chain).

**Inputs.** Everything: goal, requirement, verdict, ranked strategies, simulation results, narration, catalog snapshot version, timings.

**Outputs.** `FinalRecommendation` API response; DB writes finalized (`simulation_results`, `recommendation_outputs`, `spend_simulations.status='completed'`).

*(v1.1)* `FinalRecommendation` adopts the **Recommendation Package** contract from [recommendation-engine-design-v1.md](recommendation-engine-design-v1.md) §5: goal summary · feasibility assessment · required reward currency · portfolio assessment · reward gap analysis · recommended strategy · spend allocation plan · opportunity breakdown · transfer plan · timeline projection · expected accumulation · estimated time to goal · strategy score (+ breakdown) · supporting calculations · key assumptions · **risks & limitations** · next actions · alternative strategies. Every field maps to a deterministic pipeline artifact; none is LLM-originated.

**Internal responsibilities.** Response shaping; marking `assumed` flags for the UI ("based on default spend profile — edit to refine"); attaching snapshot version + engine versions to the stored artifacts (regeneration lineage); structured request-level telemetry (stage timings, candidate counts).

**Dependencies.** Orchestrator/API layer (owner); Database.

**Failure scenarios.** Partial persistence → the response still returns (user-facing result beats bookkeeping); failed writes retried once and logged. Nothing user-visible depends on write success.

**AI vs deterministic.** Fully deterministic.

---

## 3. Engine Interaction Diagram

### 3.1 Who calls whom

```
                    ┌──────────────────────────────────────────────┐
                    │   API LAYER (FastAPI route + Orchestrator)    │
                    │   owns the pipeline; the ONLY component      │
                    │   that calls engines; owns all DB writes      │
                    └──┬────────┬──────────┬──────────┬────────┬───┘
                       │        │          │          │        │
          Stage 1,10   │        │ 2,3,4    │ 5        │ 6,7,9  │ 8
                       ▼        ▼          ▼          ▼        ▼
                ┌──────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌──────────┐
                │    AI    │ │ Reward  │ │ Reward  │ │ Optimiza-│ │ Simula-  │
                │ Reasoning│ │Knowledge│ │Valuation│ │   tion   │ │  tion    │
                │  Layer   │ │ Engine  │ │ Engine  │ │  Engine  │ │  Engine  │
                └────┬─────┘ └────┬────┘ └────┬────┘ └────┬─────┘ └────┬─────┘
                     │            │           │           │            │
                     ▼            ▼           │      (pure calls) (pure calls)
                 LLM API      Database        └───────────┴──────┬─────┘
               (OpenAI/                                          │
                Gemini)                          Valuation's pure functions
                                                 (transfer math, cap-aware
                                                  earn rates) are the shared
                                                  calculation vocabulary
```

**Ownership boundaries:**

| Boundary | Rule |
|---|---|
| **Orchestrator ↔ engines** | Engines never call each other *across* stage boundaries and never talk to the orchestrator's state; they are functions the orchestrator composes. The two sanctioned intra-stage exceptions: Optimization and Simulation may call **Valuation's pure functions** (shared math), never its enumeration API. |
| **Knowledge Engine ↔ Database (catalog)** | The Knowledge Engine is the *sole* reader of catalog tables and owner of the snapshot abstraction. No other engine issues SQL against `cards`, `reward_categories`, `card_transfer_partners`, `reward_milestones`, `award_charts`. |
| **Orchestrator ↔ Database (user/simulation/recommendation layers)** | User-layer reads and *all* writes go through the orchestrator's repository functions. Engines stay pure — this is what makes them fixture-testable. |
| **AI Reasoning Layer ↔ LLM API** | Only this layer holds an LLM client. It exposes exactly two operations: `extract_intent(text, vocab) → ParsedGoalIntent \| ClarificationRequest` and `narrate(results) → RecommendationNarration`. No other component can reach an LLM. |

**Shared dependencies:** the catalog snapshot (produced by Knowledge, embedded in `PlanningContext`, read by Valuation/Optimization/Simulation) and Valuation's pure-math functions. Both are data/function sharing, not control-flow coupling.

**Where data enters and leaves the system:**
- *Enters:* user input via the API (goals, spend profiles, wallet, clarification answers); catalog data via admin seeding/curation (outside this pipeline — the semi-manual update workflow from MVP scope §5H); vocabulary → LLM at Stage 1.
- *Leaves:* the `FinalRecommendation` response to the frontend; structured payloads → LLM API at Stages 1/10 (the only external egress besides the DB — and it must never include another user's data, only this request's results and public catalog vocabulary).

### 3.2 The catalog snapshot (shared read model)

The Knowledge Engine loads active catalog rows into typed, immutable in-memory structures with a version stamp (MVP: max `updated_at` across catalog tables; post-MVP: explicit version). One request = one snapshot. The whole MVP catalog (8 cards × ~8 categories, tens of partners/links/charts) is a few hundred rows — process-cached with short TTL, refreshed on admin update. This is a read model, not new infrastructure.

---

## 4. Data Flow

How each major object is born, evolves, and comes to rest:

| Object | Born at | Transformed by | Final resting place |
|---|---|---|---|
| **Raw goal text** | User, Stage 1 input | → `ParsedGoalIntent` (LLM proposal, unvalidated) | Discarded after parse (kept in logs) |
| **ParsedGoalIntent** | Stage 1 | Validated + resolved → `TravelGoal`; or bounced back as `ClarificationRequest` | Superseded by `TravelGoal` |
| **TravelGoal** | Stage 2 | Enriched with `RewardRequirement` (3); embedded in `PlanningContext` (4) | `user_goals` row (persisted at birth, status-tracked for life) |
| **RewardRequirement** | Stage 3 | Consumed by feasibility (6), ranking (9), narration (10) | Denormalized to `user_goals.target_miles` |
| **PlanningContext** | Stage 4 | Read-only input to 5–9; **never mutated** — Flow B creates a *new* one | Ephemeral; snapshot version persisted with results for reproducibility |
| **OpportunitySet** | Stage 5 | Bounded by gate (6); composed into strategies (7); `valuation_notes` flow to narration (10) | Ephemeral; surviving opportunities live on inside strategies |
| **FeasibilityVerdict** | Stage 6 | Feasible → gate opens; infeasible → becomes the recommendation payload (10) | Embedded in final response |
| **CandidateStrategy[]** | Stage 7 | Each simulated (8) → corrected by simulation where they disagree → scored (9) | Winning + alternative strategies inside `simulation_results` JSONB + response |
| **SpendAllocation** (per strategy) | Stage 7 | Simulated month-by-month (8); user pins from `simulation_line_items` respected | `simulation_results.card_allocations` JSONB |
| **SimulationResult[]** | Stage 8 | Scored (9); aggregates narrated (10) | `simulation_results` rows |
| **RankedStrategy[]** | Stage 9 | Top + alternates narrated (10); assembled (11) | Ordering + `score_breakdown` in response; score → `optimization_score` |
| **RecommendationNarration** | Stage 10 | Validated against its own input payload; assembled (11) | `recommendation_outputs` rows (with `model_version`) |
| **FinalRecommendation** | Stage 11 | — | API response; reconstructable from persisted lineage |

The invariant across this table: **objects only gain structure moving downstream — nothing is re-parsed, re-guessed, or re-derived from language after Stage 2.** The single trust boundary is crossed exactly once.

---

## 5. Responsibility Matrix

| # | Stage | Responsible engine | Consumes | Produces | AI / Rule | Primary owner (module path) |
|---|---|---|---|---|---|---|
| 1 | Intent Extraction & Clarification | AI Reasoning Layer | Raw text, vocabulary | `ParsedGoalIntent` / `ClarificationRequest` | **AI** (schema-validated) | `ai_reasoning/intent.py` |
| 2 | Goal Resolution & Validation | Reward Knowledge Engine | `ParsedGoalIntent`, catalog | `TravelGoal` (persisted) | Rule | `knowledge/goal_resolution.py` |
| 3 | Reward Requirement Estimation | Reward Knowledge Engine | `TravelGoal`, award chart | `RewardRequirement` | Rule | `knowledge/requirements.py` |
| 4 | Planning Context Assembly | Orchestrator + Knowledge | Goal, user state, snapshot | `PlanningContext` | Rule | `pipeline/context.py` |
| 5 | Opportunity Enumeration & Valuation | Reward Valuation Engine | `PlanningContext` | `OpportunitySet` | Rule | `valuation/opportunities.py` |
| 6 | Feasibility Gate | Optimization Engine | `OpportunitySet`, requirement | `FeasibilityVerdict` | Rule | `optimization/feasibility.py` |
| 7 | Candidate Strategy Generation | Optimization Engine | Opportunities, context | `CandidateStrategy[]` | Rule | `optimization/strategies.py` |
| 8 | Timeline Simulation | Simulation Engine | Strategy + context (×N) | `SimulationResult[]` | Rule | `simulation/projector.py` |
| 9 | Ranking & Selection | Optimization Engine | Candidates + simulations | `RankedStrategy[]` | Rule | `optimization/ranking.py` |
| 10 | Explanation & Narration | AI Reasoning Layer | Ranked results (only) | `RecommendationNarration` | **AI** (validated + fallback) | `ai_reasoning/narration.py` |
| 11 | Assembly & Persistence | Orchestrator | Everything | `FinalRecommendation` + DB writes | Rule | `pipeline/assemble.py` |

Nine deterministic stages, two AI stages — both AI stages structurally incapable of injecting numbers into calculations (Stage 1's output is fully re-validated; Stage 10's output is post-validated prose over finished numbers).

---

## 6. Sequence Diagram

Flow A, feasible path, no clarification turns:

```mermaid
sequenceDiagram
    autonumber
    participant FE as Frontend
    participant API as API / Orchestrator
    participant AI as AI Reasoning Layer
    participant LLM as LLM API
    participant KN as Knowledge Engine
    participant VAL as Valuation Engine
    participant OPT as Optimization Engine
    participant SIM as Simulation Engine
    participant DB as Database

    FE->>API: POST /goals { "SQ business, HYD→SIN, 8 months" }
    API->>KN: get_catalog_snapshot()
    KN->>DB: read catalog layer (cached, versioned)
    DB-->>KN: catalog rows
    KN-->>API: snapshot v42

    rect rgb(245, 240, 225)
    note over API,LLM: AI edge 1 — intent (proposal only)
    API->>AI: extract_intent(text, vocabulary)
    AI->>LLM: constrained structured-output call
    LLM-->>AI: draft intent
    AI-->>API: ParsedGoalIntent (or ClarificationRequest → FE, loop)
    end

    API->>KN: resolve_and_validate(intent, snapshot)
    KN-->>API: TravelGoal (route supported, chart locked)
    API->>DB: INSERT user_goals
    API->>KN: estimate_requirement(goal)
    KN-->>API: RewardRequirement (70k miles + buffer, taxes)

    API->>DB: read user_cards, spend profile
    API->>API: assemble PlanningContext (frozen, snapshot v42)

    API->>VAL: enumerate_opportunities(context)
    VAL-->>API: OpportunitySet (valued, eligibility-filtered)

    API->>OPT: check_feasibility(opportunities, requirement)
    OPT-->>API: FeasibilityVerdict: feasible
    note over API,OPT: infeasible → skip to narration with adjustment options

    API->>OPT: generate_candidates(opportunities, context)
    OPT->>VAL: pure valuation calls (cap-aware re-pricing)
    OPT-->>API: 4 CandidateStrategies

    loop per candidate
        API->>SIM: simulate(strategy, context)
        SIM->>VAL: pure transfer-math calls
        SIM-->>API: SimulationResult (monthly ledger)
    end
    API->>DB: INSERT simulation_results

    API->>OPT: rank(candidates, simulations, requirement)
    OPT-->>API: RankedStrategy[] + score breakdowns

    rect rgb(245, 240, 225)
    note over API,LLM: AI edge 2 — narration (phrasing only)
    API->>AI: narrate(ranked results payload)
    AI->>LLM: single call, no tools, no retrieval
    LLM-->>AI: narration draft
    AI->>AI: validate every number/name against payload
    AI-->>API: RecommendationNarration (or template fallback)
    end
    API->>DB: INSERT recommendation_outputs

    API-->>FE: FinalRecommendation (strategies + simulations + narration + lineage)
```

The two shaded blocks are the complete AI surface of the system. Everything between them is replayable byte-for-byte from `(goal, user context, snapshot v42)`.

---

## 7. Dependency Graph

Compile-time dependencies (what imports what), which is what governs testability and reuse:

```
            ┌─────────────────┐
            │  domain types   │   Pydantic models: TravelGoal, PlanningContext,
            │ (shared kernel) │   RewardOpportunity, CandidateStrategy, ...
            └────────┬────────┘   depends on nothing
                     │ (everyone imports types; nothing below imports "up")
   ┌───────────┬─────┴─────┬──────────────┬─────────────┐
   ▼           ▼           ▼              ▼             ▼
┌────────┐ ┌─────────┐ ┌──────────┐ ┌───────────┐ ┌──────────┐
│Knowledge│ │Valuation│ │Simulation│ │Optimization│ │    AI    │
│ Engine │ │ Engine  │ │  Engine  │ │   Engine   │ │Reasoning │
└───┬────┘ └─────────┘ └────┬─────┘ └─────┬──────┘ └────┬─────┘
    │           ▲           │             │             │
    │           └───────────┴─────────────┘             │
    │            (pure-math imports only)               │
    ▼                                                   ▼
 Database                                            LLM API
 (catalog)
                     ┌──────────────────┐
                     │   Orchestrator   │  imports all five engines
                     │  (pipeline/)     │  + user-layer repositories
                     └──────────────────┘
```

| Engine | Depends on | Depended on by | Independently reusable? |
|---|---|---|---|
| **Domain types** | — | everything | Yes — it's the shared vocabulary |
| **Knowledge** | types, DB | Orchestrator | Yes — any future feature needing catalog reads (admin UI, data-freshness checker) uses it as-is |
| **Valuation** | types only | Optimization, Simulation (pure functions); Orchestrator | **Most reusable module in the system** — pure functions; powers future "what's this card worth for me" features standalone |
| **Simulation** | types, Valuation (math) | Orchestrator | Yes — Flow B and the public landing-page simulator call it directly, no strategy pipeline needed |
| **Optimization** | types, Valuation (math) | Orchestrator | Partly — feasibility/ranking are general; archetype generation is product-specific |
| **AI Reasoning** | types, LLM client | Orchestrator | Yes — intent/narration are generic operations over typed payloads |
| **Orchestrator** | all of the above | FastAPI routes | No — it *is* the product flow, and that's correct |

Key structural facts:
- **No cycles.** Knowledge never imports Valuation; Valuation never imports Optimization; nothing imports the orchestrator.
- **Completely independent of each other:** Knowledge ⊥ AI Reasoning ⊥ {Valuation, Optimization, Simulation}. The deterministic-math trio shares only Valuation's pure functions, one-directionally.
- **The DB touches two components only:** Knowledge (catalog reads) and the orchestrator's repositories (user-layer reads, all writes). Three of five engines are DB-free — they can be tested exhaustively with in-memory fixtures, which is where the tdd skill's mandate lands hardest.

---

## 8. Design Review

An honest pass over this design's weak points.

### 8.1 What's missing (and deliberately deferred vs. genuinely absent)

| Gap | Verdict |
|---|---|
| **Catalog data-freshness/validation tooling.** The pipeline trusts the snapshot completely; a wrong transfer ratio produces a confidently wrong recommendation — the worst failure class this product has. The schema has `is_active` flags but nothing validates data coherence (card with transfer link but no earn rates, chart rows with absurd values). | **Genuinely missing — build alongside the Knowledge Engine.** A `validate_catalog()` invariant-check run on snapshot load (and in CI against seeds) is cheap and directly protects the core differentiator (trust). Not a new engine; a function inside Knowledge. |
| **Goal re-planning / progress tracking** ("it's month 3, am I on track?"). | Deferred, correctly — the pipeline shape already supports it (re-run Flow B against updated balances). Needs no architectural provision now beyond what exists. |
| **Award availability** (miles ≠ seats). | Excluded by MVP scope explicitly. The narration must state the assumption ("assumes saver availability") — a copy requirement, not an engine. |
| **Rate limiting / abuse control on LLM stages.** | Missing but trivial — FastAPI middleware; note it for the API spec, not this document's concern. |

### 8.2 Misplaced-responsibility risks

- **Stage 4 (context assembly) sits in the orchestrator.** Defensible (it composes *user* state with catalog state, and the orchestrator owns user reads), but watch it: if it accretes reward logic (e.g., "normalize spend profile" growing category-inference rules), that logic belongs in Knowledge. Keep assembly dumb.
- **Feasibility (6) in Optimization rather than Valuation.** It computes a bound using valuation math, so an argument exists for Valuation. It stays in Optimization because its *inverse* problems (smallest timeline extension, best single card add) are optimization questions, and splitting the gate's two halves across engines would be worse. Revisit only if the gate grows independent of the generator.
- **The known tension in root `CLAUDE.md`:** it lists "orchestration" as an LLM job; this document confines LLM orchestration to the conversational edge (§0.2). That's an intentional narrowing, flagged here so it gets reconciled in CLAUDE.md rather than rediscovered as a contradiction later.

### 8.3 Bottlenecks

- **LLM latency dominates end-to-end time.** Two calls ≈ 5–20s combined. Deterministic core over 8 cards / 8 categories / ≤8 candidates / ≤24 months is trivially fast (thousands of arithmetic ops — milliseconds, pure Python; NumPy/OR-Tools are not needed at MVP scale). The v2 **30s** budget holds in the common case but has little slack for a slow narration call — so the streaming lever (structured results as soon as Stage 9 finishes, narration second) should be treated as the *planned* API shape, not a later optimization. An API-shape decision, not an architecture change.
- **Catalog snapshot rebuild** is a few hundred rows — a non-issue; the TTL cache is a nicety, not a necessity.
- **Synchronous request risk:** a hung LLM call is the only realistic way to blow the budget → hard timeouts on both AI stages (Stage 1: fall back to form; Stage 10: fall back to template) make the worst case bounded and non-fatal. No queue needed for this.

### 8.4 Hidden complexity (where the estimate is most likely wrong)

1. **Cap-and-milestone interaction in allocation (Stage 7).** Greedy allocation with marginal-rate awareness plus a milestone post-pass covers the MVP's 8 cards, but the interaction is the one place with genuine combinatorial teeth. Contained by: candidates bounded, simulation (Stage 8) catches any generator overstatement, and the archetype frame means a mildly sub-optimal allocation still produces an honest, explainable plan. The escape hatch (OR-Tools behind the same `generate_candidates` interface) exists but must be *earned by real failing cases*, per "heuristic-first."
2. **Clarification-loop state (Stage 1).** Multi-turn state between stateless HTTP requests. MVP answer: the accumulating `ParsedGoalIntent` lives client-side and is resubmitted whole each turn — server stays stateless, no session store. Slightly bigger payloads; vastly simpler backend.
3. **Narration validation (Stage 10).** "Every number must exist in the payload" needs care around formatting (₹8L vs 800000, rounding, "about 92k"). Normalize before matching; tolerate rounding; when in doubt, regenerate or fall back. Accept that validation is conservative — a falsely-rejected eloquent narration costs a template; a falsely-accepted fabricated number costs trust.
4. **Region mapping (Stage 2).** City→region looks trivial until multi-city origins and stopovers arrive. MVP: a literal dict for supported routes. Resist generalizing it.

### 8.5 Areas most likely to change (isolate them now)

| Volatile element | Isolation strategy (already in the design) |
|---|---|
| Ranking weights | Versioned config, not code (`optimization/ranking.py` reads it) |
| Candidate archetypes | Each archetype a separate generator function behind one interface; add/remove without touching allocation math |
| Award charts / ratios / earn rates | Data, not code (already the schema's stance); snapshot versioning gives lineage |
| Allocation algorithm (greedy → OR-Tools) | Behind `generate_candidates()`; callers see `CandidateStrategy[]` either way |
| LLM provider/prompts | Entirely inside AI Reasoning Layer; two functions to swap |
| Buffer %, candidate cap, timeouts | One `pipeline_settings` config object |

### 8.6 Future scalability concerns (noted, not built)

Multi-goal optimization (two goals competing for the same spend) is the first future feature that strains the shape — `PlanningContext` would carry multiple requirements and Stage 7's objective becomes multi-target. The stage boundaries survive; the generator internals don't. Fine: that's exactly where the complexity belongs. Multi-airline and hotels are, by contrast, pure data additions (more partners, more charts) — the pipeline is already program-agnostic; only Stage 2's region mapping and Stage 1's vocabulary grow.

---

## 9. Recommendations

Concrete, decided recommendations for the in-flight engine specs and CLAUDE.md:

1. **Do not create standalone Opportunity or Ranking Engines.** Home them as `valuation/opportunities.py` and `optimization/ranking.py` respectively (rationale in §0.3). The in-design "Reward Opportunity Engine" and "Ranking Engine" documents should be written as *module specs within* the Valuation and Optimization Engine docs. The five-engine decomposition in root `CLAUDE.md` stands.
2. **Retitle "Strategy Generation Engine" to the Optimization Engine's spec.** One system, one name; CLAUDE.md's name wins. The strategy-generation doc becomes the Optimization Engine spec covering Stages 6, 7, 9.
3. **Amend root `CLAUDE.md`'s LLM "orchestration" bullet** to "conversational orchestration (clarification flow) — pipeline orchestration is deterministic code." Cheap edit; prevents a future contributor from putting LangGraph in the middle of the pipeline citing CLAUDE.md.
4. **Defer LangGraph entirely; adopt if/when the clarification loop grows genuine branching.** A linear pipeline plus a client-held clarification loop needs zero graph framework. PydanticAI for the two structured LLM calls is sufficient. (Tech-stack listing ≠ obligation to use at MVP.)
5. **Build `validate_catalog()` invariant checks with the Knowledge Engine, from day one** (§8.1). Wrong catalog data is this product's existential failure mode; a validation function is the cheapest insurance available.
6. **Persist lineage on every artifact:** catalog snapshot version + engine version on `simulation_results` and `recommendation_outputs`. Makes "why did it recommend this in June?" answerable forever — the audit trail behind the explainability promise. (Small additive schema change: one `snapshot_version` column or metadata key each.)
7. **Implement the narration fallback templates in the same PR as the narration itself**, not later. The fallback is what makes "numbers ship regardless of LLM availability" true; retrofitting it under incident pressure is how it ends up never existing.
8. **Keep the request synchronous; no queues/workers/events at MVP** (§8.3). Revisit only if measured LLM latency breaks the 60s budget, and reach for response streaming before reaching for infrastructure.
9. **Order of implementation follows the dependency graph:** domain types → Knowledge (+ `validate_catalog`, seeds) → Valuation → Simulation → Optimization → AI Reasoning → orchestrator. Each engine lands fully unit-tested against fixtures (tdd skill mandate) before the next begins; the pipeline composes them last. This order also front-loads the highest-trust components.

---

*Document maintained by: OptiMILES Backend Team*
*v1.0.0 (2026-07-03) — Initial execution blueprint.*
*v1.1.0 (2026-07-03) — Reconciled with the mirrored Notion engine docs: preference-aware ranking + portfolio-utilization dimension, explicit validation (Stage 7) and pruning (Stage 9) steps, `PortfolioAssessment` output on the feasibility gate, Recommendation Package payload contract, 30s target from MVP Scope v2. Module homes in §0.3 confirmed against SGE-001/SRE-001/RKE-001. The reward-currency-as-entity decision is now made (adopted — [backend-build-plan-v1.md](backend-build-plan-v1.md) D-1/§3); implementation follows the build plan's phases. Next review: end of build Phase 1.*
