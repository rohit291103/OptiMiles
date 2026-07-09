# OptiMiles — Simulation Engine Specification v1

**Document ID:** SIM-001
**Version:** v1.0
**Status:** Active — implementation reference for build-plan Phase 3
**Source:** Mirrored from Notion `Simulation_Engine_Design_v1` (created 2026-07-03) on 2026-07-04.

---

> **Reconciliation note (2026-07-04):** this doc names the engine's neighbors "Reward Opportunity Engine," "Strategy Generation Engine," and "Strategy Ranking Engine." Per [system-execution-flow-v1.md](system-execution-flow-v1.md) §0.3, those are modules of Valuation (`valuation/opportunities.py`) and Optimization (`optimization/strategies.py`, `optimization/ranking.py`), not standalone engines — the Simulation Engine itself is one of the five and stays a standalone module (`simulation/projector.py`, Stage 8), matching root `CLAUDE.md`. This spec is otherwise the primary design reference for Phase 3 — read alongside system-execution-flow-v1.md Stage 8 and the tracker's Phase-3 reviewer note (confirm Simulation is the cap-truth layer correcting Stage 5's static blend, per [2026-07-04-phase2-valuation-engine-math-contract.md](../decisions/2026-07-04-phase2-valuation-engine-math-contract.md) item 3).

---

# 1. Purpose

## Objective

The Simulation Engine projects the future execution of a candidate strategy over time.

Its purpose is to estimate how rewards accumulate, when milestones are achieved, how transfers occur and when the user's travel goal becomes achievable.

Unlike the Strategy Generation Engine, which creates execution plans, or the Strategy Ranking Engine, which selects the best strategy, the Simulation Engine validates a strategy by forecasting its expected outcome.

The Simulation Engine produces deterministic projections that enable users to understand **what will happen if they follow a particular strategy**.

---

# 2. Scope

## In Scope

The Simulation Engine is responsible for:

- Projecting monthly reward accumulation
- Tracking reward balance growth
- Forecasting milestone completion
- Simulating transfer events
- Estimating goal completion timeline
- Producing execution timelines
- Generating simulation metrics

## Out of Scope

The engine is not responsible for:

- Strategy generation
- Strategy ranking
- Reward opportunity discovery
- Reward calculations
- Recommendation generation
- User explanations

---

# 3. Architecture Decisions

| ID | Decision |
|---|---|
| AD-01 | Simulations are deterministic. |
| AD-02 | MVP assumes fixed monthly spending. |
| AD-03 | Simulation runs until the goal is achieved or the strategy becomes impossible. |
| AD-04 | The engine produces technical simulation outputs only. |
| AD-05 | The Recommendation Engine converts simulation results into user-friendly execution plans. |
| AD-06 | Historical reward rules are respected based on version validity. |

*(Repo note on AD-06: MVP has one active catalog snapshot per request — no time-travel across catalog versions within a single simulation run. "Historical rule validity" becomes relevant only if a goal is re-simulated after a catalog update; the snapshot-locking already in place (build-plan D-1, `catalog_snapshot_version` lineage) is the mechanism, not a new one.)*

---

# 4. Responsibilities

The Simulation Engine validates a strategy by projecting its execution over time.

Its responsibilities include:

- Monthly reward projection
- Reward balance tracking
- Milestone forecasting
- Transfer event simulation
- Goal completion forecasting
- Simulation reporting

The engine never modifies a strategy.

---

# 5. Simulation Model

The simulation operates as a month-by-month projection. For each simulation cycle, the engine evaluates:

1. Monthly spend
2. Reward accumulation
3. Milestone progress
4. Reward balance update
5. Transfer eligibility
6. Transfer execution
7. Goal progress

The cycle repeats until: goal achieved, strategy exhausted, or simulation limit reached.

---

# 6. Simulation Workflow

```
Receive Candidate Strategy
        │
        ▼
Initialize Simulation
        │
        ▼
Apply Monthly Spend
        │
        ▼
Update Reward Balances
        │
        ▼
Evaluate Milestones
        │
        ▼
Execute Eligible Transfers
        │
        ▼
Evaluate Goal Progress
        │
        ▼
Goal Achieved?
      │
 ┌────┴────┐
 │         │
No        Yes
 │         │
 ▼         ▼
Next Month Publish Results
```

---

# 7. Simulation Outputs

## 7.1 Reward Timeline

Month-by-month reward accumulation.

## 7.2 Reward Balance Timeline

Growth of reward balances over time (example): 12,000 → 18,000 → 27,500 → 45,000.

## 7.3 Milestone Timeline

Forecast of milestone completion. Examples: ₹4L Spend Completed, Welcome Bonus Earned, Annual Spend Bonus Achieved.

## 7.4 Transfer Timeline

Expected transfer events. Example: Month 8 → Transfer HDFC Reward Points → KrisFlyer.

## 7.5 Goal Completion Timeline

Estimated month in which the goal becomes achievable. Example: Goal Achieved → Month 11.

## 7.6 Simulation Metrics

Examples: Total Rewards Earned, Total Transfers, Total Annual Fees, Total Reward Balance, Time to Goal, Milestones Completed.

*(Repo mapping: §7.1–7.6 correspond to `SimulationResult`'s month-indexed ledger (`domain/simulation.py`: `MonthLedgerEntry`, `TransferExecution`) plus aggregates `months_to_goal`, `miles_at_target_date`, `total_fees_inr`, `buffer_achieved` defined in system-execution-flow-v1.md Stage 8.)*

---

# 8. Inputs

- Candidate Strategy
- User Spending Profile
- Reward Rules
- Reward Opportunities
- Transfer Relationships
- Milestones
- User Constraints

---

# 9. Business Rules

- **BR-01** Simulation must remain deterministic.
- **BR-02** Monthly spending remains constant throughout the simulation unless explicitly modified.
- **BR-03** Milestones are awarded only after their qualifying conditions are satisfied.
- **BR-04** Transfers occur only when transfer eligibility requirements are met.
- **BR-05** Expired promotions must not influence future simulation periods.
- **BR-06** Historical business rules apply only during their valid period.
- **BR-07** Simulation never changes strategy decisions.
- **BR-08** Simulation stops immediately when the goal becomes achievable.
- **BR-09** Simulation must expose every significant event during execution.
- **BR-10** Simulation outputs must be reproducible using identical inputs.

*(Repo note: BR-10 is the determinism test mandated by backend-build-plan-v1.md rule 8 — same goal + user context + snapshot version ⇒ byte-identical results. BR-08's "stops immediately" and Stage 8's `misses_goal` labeling both need a clean tie-in: if the horizon ends before the goal is reached, the simulation still returns the full ledger through the horizon with `misses_goal=true`, rather than an early abort with no data — ranking needs the full picture to score a near-miss candidate.)*

---

# 10. Relationships

- **Strategy Generation Engine** — provides candidate strategies.
- **Reward Knowledge Engine** — provides reward rules and business knowledge.
- **Reward Opportunity Engine** — provides earning opportunities referenced by strategies.
- **Strategy Ranking Engine** — uses simulation outputs as one input during evaluation.
- **Recommendation Engine** — consumes simulation outputs to produce: Executive Summary, Overall Strategy, User Timeline, Action Plan.

*(Repo mapping: "Strategy Generation/Ranking Engine" = `optimization/strategies.py` / `optimization/ranking.py`; "Reward Opportunity Engine" = `valuation/opportunities.py`. Per system-execution-flow-v1.md §3.1, Simulation may call **Valuation's pure math functions** (`transfer_math.py`) directly — the one sanctioned intra-stage exception — but never Valuation's enumeration API.)*

---

# 11. Failure Handling

| Scenario | Engine Behaviour |
|---|---|
| Missing reward rules | Stop simulation and report missing knowledge |
| Missing transfer rule | Ignore transfer and continue where possible |
| Invalid milestone | Exclude milestone from simulation |
| Strategy cannot achieve goal | Return unsuccessful simulation result |
| Missing spending profile | Request upstream completion before simulation |
| Conflicting business rules | Use active validated rule version and report conflict |

---

# 12. Assumptions

- Monthly spending remains fixed for the duration of the simulation.
- Business rules are validated by the Reward Knowledge Engine.
- Candidate strategies are executable.
- Reward calculations are deterministic.
- Reward opportunities remain valid unless their lifecycle changes.

---

# 13. Constraints

- The engine cannot generate strategies.
- The engine cannot rank strategies.
- The engine cannot recommend products.
- The engine cannot explain results.
- The engine cannot personalize execution plans.

---

# 14. Future Extensions

Variable monthly spending, income growth modelling, probability-based forecasting, Monte Carlo simulation, family reward pooling, dynamic transfer bonus forecasting, award seat availability forecasting, multi-goal simulation, "what-if" scenario comparisons.

---

# Engine Position

```
Reward Knowledge Engine
            │
            ▼
Reward Opportunity Engine
            │
            ▼
Strategy Generation Engine
            │
            ▼
Strategy Ranking Engine
            │
            ▼
Simulation Engine
            │
            ▼
Recommendation Engine
```

*Repo reality (system-execution-flow-v1.md §1): Simulation is **Stage 8**, running per-candidate straight after Strategy Generation (Stage 7) and **before** Ranking (Stage 9) — ranking scores simulated outcomes, not the reverse order shown above. The source doc's ordering reflects the original Notion draft sequence; the build already implements the corrected Stage 8-before-9 order.*

---

# Recommendation Engine Consumption

The Simulation Engine produces structured data. The Recommendation Engine transforms this data into a user-facing recommendation.

## Executive Summary

Goal, Estimated Timeline, Expected Reward Balance, Required Cards.

## Overall Strategy (example)

**Phase 1 (Months 1–3):** Route shopping spends through SmartBuy. Complete ₹4L Infinia milestone. Accumulate reward points.

**Phase 2 (Months 4–8):** Apply for HSBC TravelOne. Route travel bookings through HSBC Travel Portal. Continue optimized spend allocation.

**Phase 3 (Months 9–11):** Transfer eligible points to KrisFlyer. Redeem miles. Book Singapore Airlines Business Class.

## Detailed Timeline

Users may expand the recommendation to view: monthly spend, monthly rewards, milestone progress, transfer events, goal completion progress. This layered presentation keeps the recommendation understandable while preserving detailed simulation data for users who wish to explore it.

---

# End of Specification
