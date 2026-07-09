# OptiMiles — Optimization Engine Specification v1

**Document IDs consolidated:** SGE-001 (`Strategy_Generation_Engine_Design_v1`), SRE-001 (`Strategy Ranking Engine Design`)
**Version:** v1.0
**Status:** Active
**Source:** Mirrored and consolidated from two Notion docs (2026-06-28) on 2026-07-03. Per [system-execution-flow-v1.md](system-execution-flow-v1.md) §0.3 and root `CLAUDE.md`'s five-system decomposition, "Strategy Generation Engine" and "Strategy Ranking Engine" are **modules of the Optimization Engine**, not standalone engines. This spec covers the whole engine: feasibility (`optimization/feasibility.py`), generation (`optimization/strategies.py`), and ranking (`optimization/ranking.py`) — blueprint Stages 6, 7 and 9.
**Also see:** [strategy-ranking-engine-design-v1.md](strategy-ranking-engine-design-v1.md) — a newer (2026-07-03) Notion draft of the ranking module with additional architecture decisions (AD-01–06) and business rules (BR-01–08) not yet folded into §3 below; consult both until merged.

---

# 1. Purpose

The Optimization Engine turns a valued `OpportunitySet` into a ranked set of complete, executable reward strategies. It owns three responsibilities:

1. **Feasibility** — can this goal be achieved at all within the horizon; if not, which adjustments would make it achievable.
2. **Strategy generation** — compose opportunities into candidate strategies, each a complete execution plan.
3. **Ranking** — score validated, simulated candidates and select the primary recommendation plus alternatives.

Everything in this engine is deterministic. No LLM proposes, adjusts, vetoes, or reorders strategies.

---

# 2. Strategy Generation module (from SGE-001)

## 2.1 Inputs

| Input | Description |
|---|---|
| Goal | User's travel objective (`TravelGoal`) |
| User Profile | Spending behaviour, preferences and constraints (in `PlanningContext`) |
| Portfolio | Existing cards, reward balances, memberships (in `PlanningContext`) |
| Reward Requirement | Required currency, miles/points, transfer ecosystem |
| Reward Opportunities | Valued earning paths, milestones, transfer paths (`OpportunitySet`) |

Inputs are assumed already validated by earlier pipeline stages.

## 2.2 Outputs

A **Candidate Strategy Set** — each strategy a complete execution plan: cards used, new cards required (if any), spend allocation, opportunities utilized, transfer path, expected accumulation, estimated timeline, milestones. No ranking at this stage.

## 2.3 Strategy types → generation archetypes

The Notion design's three strategy types map onto the blueprint's four archetypes:

| SGE strategy type | Blueprint archetype(s) |
|---|---|
| **Existing Portfolio Strategy** — current cards only; lowest acquisition cost; highest trust; **always generated first** | *Status quo optimized* (always generated; also the baseline all others are compared against) + *Simplest viable* |
| **Portfolio Expansion Strategy** — new card(s) when the portfolio can't achieve the goal efficiently; must justify why | *One new card* (one candidate per justifiable acquisition, capped) |
| **Hybrid Strategy** — existing cards + only necessary additions, allocation optimized across all | *One new card* and *Concentrated/milestone* combinations |

## 2.4 Workflow

```
Receive inputs
   ↓ Generate Existing Portfolio Strategy   (always first — BR-01)
   ↓ Evaluate goal feasibility              (gate already ran at Stage 6; here: per-strategy sufficiency)
   ↓ If goal not efficiently achievable → generate Portfolio Expansion strategies
   ↓ Generate Hybrid strategies
   ↓ Validate business rules (BR-01…BR-07) + completeness    ← explicit validation step
   ↓ Return Candidate Strategy Set
```

## 2.5 Business rules

| ID | Rule |
|---|---|
| BR-01 | Always generate an Existing Portfolio Strategy before considering new cards. |
| BR-02 | Never recommend additional cards unless they provide meaningful improvement over the existing portfolio. |
| BR-03 | Generate every feasible strategy that satisfies the business rules. *(MVP realization: bounded archetype coverage of the structurally distinct strategy space — see [recommendation-engine-design-v1.md](recommendation-engine-design-v1.md) §6.2 C-2.)* |
| BR-04 | Never generate strategies that violate user constraints (max annual fee, no additional cards, preferred banks, spending limits). |
| BR-05 | Every generated strategy must be a complete execution plan; partial strategies are invalid. |
| BR-06 | Generation is independent of ranking — this module produces candidates only. |
| BR-07 | All strategies must be executable using supported reward programs, transfer partners and business rules. |

## 2.6 Exit criteria

Generation completes when every archetype has been attempted, every emitted strategy satisfies BR-01…BR-07, invalid/incomplete strategies are discarded, and a Candidate Strategy Set exists (1–2 candidates is a valid outcome for small wallets).

---

# 3. Ranking module (from SRE-001)

## 3.1 Inputs / outputs

**Inputs:** Candidate Strategy Set **with per-candidate simulation results** (ranking scores simulated outcomes, not generator estimates — blueprint Stage 8 runs between generation and ranking), user profile/preferences, goal, ranking policy config.

**Outputs:** Ranked Strategy List; Primary Strategy; Alternative Strategies. Only the highest-ranked strategy is shown by default; alternatives remain explorable.

## 3.2 Workflow

```
Receive candidates + simulations
   ↓ Remove duplicates + dominated strategies      ← explicit pruning step
   ↓ Apply business rules (hard constraints first)
   ↓ Evaluate each strategy across ranking dimensions
   ↓ Score (preference-weighted composite, config-driven)
   ↓ Rank → select primary
   ↓ Return Ranked Strategy List
```

## 3.3 Ranking dimensions

| Dimension | Blueprint sub-score |
|---|---|
| Timeline (how fast the goal is reached) | goal achievement |
| Reward value (expected rewards generated) | efficiency |
| Cost (annual fees + additional spend required) | cost |
| Complexity (cards, transfers, execution steps) | simplicity |
| Existing Portfolio Utilization | **portfolio-utilization** *(added to the blueprint's score vector in v1.1)* |
| Risk (tight caps, single-milestone dependence, long transfer chains) | risk |
| User preferences (fees, no new cards, speed, simplicity) | **weight modulation**, not a separate score — the preference profile deterministically adjusts dimension weights |

## 3.4 Business rules

| ID | Rule |
|---|---|
| BR-01 | Strategies that maximize the existing portfolio are preferred whenever meaningful. |
| BR-02 | Additional cards improve ranking only if they create significant incremental value. |
| BR-03 | **User constraints always override optimization** (hard filters before scoring). |
| BR-04 | Every ranking decision must be explainable (score breakdown per dimension is part of the output). |
| BR-05 | Strategies with negligible differences favor lower complexity (near-tie rule). |
| BR-06 | Always return one primary recommendation. |

## 3.5 Exit criteria

Every candidate evaluated; ranked list produced; one primary selected; remaining strategies preserved as alternatives. The primary passes to Recommendation Packaging (blueprint Stages 10–11).

---

# 4. Feasibility module (blueprint Stage 6 — not in the Notion drafts)

Runs *before* generation: computes the best-case miles bound from the `OpportunitySet`; if the goal is unreachable, short-circuits with computed adjustment options (smallest timeline extension, single best card addition, cabin downgrade) instead of generating strategies. Also emits the **Portfolio Assessment** (current capability, convertible balances, reward gap) used by narration and the dashboard's achievability section.

---

# 5. Module layout

```
optimization/
  feasibility.py    # Stage 6 — bound check, adjustment options, portfolio assessment
  strategies.py     # Stage 7 — archetype generators + allocation + validation (BR-01…07)
  ranking.py        # Stage 9 — prune, hard rules, preference-weighted scoring (config-driven)
```

Depends on the shared domain types and the Valuation Engine's pure math functions only; no DB access (fixture-testable end to end — `tdd` skill mandatory).
