# Decision Log — Mirror three Notion engine design docs into `/docs/architecture`

**Date:** 2026-07-04
**Area:** docs

## Context

The user added three new pages to Notion — `Reward_Opportunity_Engine_Design_v1` (ROE-001), `Strategy_Ranking_Engine_Design_v1` (SRE-001), `Simulation_Engine_Design_v1` (SIM-001), all created 2026-07-03 — and asked for them to be added to the repo. Per the Documentation Rules in root `CLAUDE.md` ("Chats are temporary. Documentation is permanent") and the `docs-sync` skill's Mode C routing, external design docs belong in `/docs/architecture`.

These three describe a six-engine pipeline (Knowledge → Opportunity → Strategy Generation → Strategy Ranking → Simulation → Recommendation), which conflicts on its face with the five-engine boundary CLAUDE.md defines and that the build plan has already implemented (`valuation/opportunities.py`, `optimization/ranking.py`). `system-execution-flow-v1.md` (v1.1, written 2026-07-03) had already reconciled this exact conflict for the two engine names that existed at the time — this pass extends the same reconciliation to the newer redrafted docs and adds the missing Simulation Engine spec (no standalone one existed yet).

## Decisions

1. **Mirrored verbatim, not restructured.** All three docs are filed as `docs/architecture/{reward-opportunity-engine-design,strategy-ranking-engine-design,simulation-engine-spec}-v1.md`, matching the existing mirroring convention (`reward-knowledge-engine-spec-v1.md`). Content is preserved as-authored; only a "Reconciliation note" is prepended to each.
2. **Reward Opportunity Engine doc → status "Reference," not "Active."** Its content (taxonomy §6, lifecycle §7, business rules §10) is genuinely useful design material beyond what Phase 2 built (merchant/promotional/loyalty opportunities, full lifecycle states are future scope), but the doc is not the implementation spec — `valuation/opportunities.py`'s own docstring is, per system-execution-flow-v1.md §0.3/§9 Recommendation 1.
3. **Strategy Ranking Engine doc → status "Reference," folded alongside the existing consolidation.** `optimization-engine-spec-v1.md` already consolidated an *older* (2026-06-28) "Strategy Ranking Engine Design" Notion page. This newer (2026-07-03) draft adds AD-01–06 and BR-01–08 not present in the older one. Rather than re-editing the Optimization spec mid-Phase-2-close, the new doc is filed standalone with a cross-reference added to `optimization-engine-spec-v1.md`'s header — both documents should be read until a future pass merges them.
4. **Simulation Engine spec → status "Active," the primary Phase 3 reference.** No simulation spec existed before this. Unlike the other two, this one is filed as `-spec-` (not `-design-`) and marked Active because it directly governs the about-to-start Phase 3 implementation (`simulation/projector.py`, Stage 8) — its ranking-dimension and business-rule content is exactly what Phase 3's TDD pass will need (BR-08 stop-on-goal-achieved semantics reconciled with Stage 8's `misses_goal` labeling; BR-10 determinism reconciled with the build plan's byte-identical-replay requirement).
5. **Ordering discrepancy flagged, not silently fixed.** All three source docs (and their "Engine Position" diagrams) show Ranking happening *before* Simulation. The actual pipeline (system-execution-flow-v1.md, already implemented through Phase 2) runs Simulation (Stage 8) before Ranking (Stage 9) — ranking must score simulated outcomes, not generator estimates. Each mirrored doc's "Engine Position" section now carries a note pointing at the corrected order rather than editing the historical diagram.

## Not done (deferred)

- Merging the two Strategy Ranking Engine drafts (2026-06-28 consolidated + 2026-07-03 standalone) into one canonical `optimization-engine-spec-v1.md` section — noted as a future cross-reference cleanup, not blocking Phase 3.
- No code changes. This is a documentation-only pass; `optimization/ranking.py` does not yet exist (Phase 4) and `simulation/projector.py` is the next implementation task (Phase 3).
