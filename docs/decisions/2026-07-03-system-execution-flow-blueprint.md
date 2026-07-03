# Decision Log — System Execution Flow v1 as Canonical Backend Blueprint

**Date:** 2026-07-03
**Area:** architecture

## Context

Backend implementation hasn't started (Phase 0), but engine design docs were being drafted in parallel across tools (ChatGPT/Notion side: Reward Opportunity Engine, Ranking Engine, Strategy Generation Engine, Simulation Engine). Nothing defined how the engines compose into one request flow — each spec risked inventing its own pipeline, ownership boundaries, and AI-vs-deterministic split. The user requested a Principal-Engineer-level end-to-end execution architecture to become the canonical blueprint every engine spec and implementation references.

Written against the repo's actual ground truth: `docs/prd/mvp_scope_1.md`, `docs/architecture/db-schema-v1.md`, and root `CLAUDE.md`'s five Core Backend Systems. Note: the prompt referenced docs ("Core Domain Model," "Strategy Generation Engine," "Recommendation Workflow") that exist outside this repo (Notion) and were not readable from this session.

## Decisions

1. **`docs/architecture/system-execution-flow-v1.md` is the canonical execution blueprint.** An 11-stage pipeline: Intent Extraction → Goal Resolution → Requirement Estimation → Context Assembly → Opportunity Enumeration → Feasibility Gate → Candidate Generation → Timeline Simulation → Ranking → Narration → Assembly. Future engine specs must reference it rather than redefine the flow.
2. **"AI sandwich" architecture.** Only Stages 1 (intent extraction) and 10 (narration) touch an LLM; Stages 2–9 and 11 are deterministic and replayable from `(goal, user context, catalog snapshot version)`. Stage 1's LLM output is a *proposal* fully re-validated against the catalog at Stage 2 (the single trust boundary); Stage 10's narration is post-validated so every number/name must exist in its input payload, with deterministic template fallback. Why: this mechanically enforces CLAUDE.md's "structured systems first" and kills the hallucination risk class (PRD risk 8-C).
3. **Pipeline orchestration is plain code, not an LLM and not LangGraph.** The flow is identical for every request, so there is no routing decision for an LLM to make. LLM "orchestration" is confined to the conversational edge (clarification loop, held client-side to keep the server stateless). LangGraph deferred until real branching exists; PydanticAI suffices for the two structured calls. Why: CLAUDE.md's anti-overengineering rules; a graph framework around a linear function is pure cost.
4. **No standalone Opportunity or Ranking Engines — the five-engine decomposition in CLAUDE.md stands.** Reward Opportunity Engine → `valuation/opportunities.py` (enumeration API of the Valuation Engine); Ranking Engine → `optimization/ranking.py` (pure scoring module, config-driven weights); "Strategy Generation Engine" is retitled as the Optimization Engine's spec. Why: each would be a shallow module — interface as complicated as its implementation — and enumeration/valuation always change together.
5. **Ownership boundaries:** Knowledge Engine is the sole reader of catalog tables and owner of a versioned, immutable per-request catalog snapshot; engines never call each other across stages (exception: Optimization/Simulation may import Valuation's pure math functions); the orchestrator owns all user-layer reads and all DB writes, keeping three of five engines DB-free and fixture-testable.
6. **Feasibility Gate (Stage 6) added as an explicit stage.** Infeasible goals short-circuit to an adjustment-options response (extend timeline / add card / downgrade cabin) instead of a dressed-up least-bad strategy. Why: honesty about impossibility is the highest-trust screen in the product and it prevents wasted compute.
7. **Synchronous single-request pipeline; no queues/workers/events at MVP.** LLM latency dominates (deterministic core is milliseconds at 8-card scale); hard timeouts + fallbacks bound the worst case inside the PRD's 30–60s budget. Streaming structured results before narration is the future lever, not infrastructure.
8. **Follow-ups the blueprint mandates:** build `validate_catalog()` invariant checks with the Knowledge Engine from day one (wrong catalog data = existential failure mode); persist catalog snapshot version + engine version on `simulation_results`/`recommendation_outputs` (small additive schema change); implement narration fallback templates in the same PR as narration; amend root `CLAUDE.md`'s LLM "orchestration" bullet to "conversational orchestration only."

## Not done (deferred)

- **CLAUDE.md "orchestration" wording amendment** (decision 8) — recommended in the blueprint (§9.3) but not applied to CLAUDE.md in this pass; should be a deliberate edit alongside the user's review of the blueprint.
- **Schema change for lineage columns** (snapshot/engine version on results tables) — recorded as a recommendation; belongs in db-schema v1.1 when backend work starts.
- **Engine-internal specs** (Knowledge, Valuation, Optimization, Simulation module interfaces in detail) — the blueprint fixes their boundaries and module homes; per-engine specs come next and must slot into it.
- **Reconciliation with the Notion-side docs** (Core Domain Model, Recommendation Workflow, etc.) — unreachable from this session; the user should check the blueprint's §0.3 mapping table against those drafts.
