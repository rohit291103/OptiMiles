# OptiMiles — Architecture Diagrams (Eraser) v1

**Date:** 2026-07-04
**Status:** Reflects build-plan Phases 0–3 complete + the 2026-07-04 catalog expansion. Paste each block into [eraser.io](https://app.eraser.io) as a cloud-architecture diagram.
**Color code:** green = built & tested · orange = next (Phase 4–5) · gray = later (Phase 6–7) or external.

---

## 1. System architecture — the five-engine backend

The load-bearing rules this diagram encodes (root `CLAUDE.md` Backend Build Rules):
only **Knowledge** and **Repositories** touch the database; only **AI Reasoning** touches an LLM;
Valuation/Simulation/Optimization are **pure functions** over a frozen `PlanningContext` snapshot;
every result row carries `catalog_snapshot_version` + `engine_version` lineage.

```eraser
// OptiMiles — System Architecture (2026-07-04)

Frontend [color: gray] {
  Landing Page [icon: nextjs]
  Goal Simulator [icon: monitor, label: "Goal Simulator (static mock, awaits Phase 7)"]
}

FastAPI Backend [icon: python] {
  API v1 [icon: globe, color: gray] {
    Goals API [icon: server, label: "POST /goals, /goals/parse"]
    Recommendation API [icon: server, label: "POST /goals/id/recommendation"]
    Simulations API [icon: server, label: "POST /simulations (public simulator)"]
    Catalog API [icon: server, label: "GET /catalog/cards"]
  }

  Pipeline Orchestrator [icon: git-branch, color: gray, label: "pipeline/ (deterministic code, no LLM orchestration)"]

  Engines {
    Knowledge Engine [icon: book-open, color: green, label: "knowledge/ — Stages 2-3, sole catalog reader"]
    Valuation Engine [icon: calculator, color: green, label: "valuation/ — Stage 5 + shared transfer math"]
    Simulation Engine [icon: clock, color: green, label: "simulation/projector.py — Stage 8 monthly ledger"]
    Optimization Engine [icon: sliders, color: orange, label: "optimization/ — Stages 6,7,9 (Phase 4, next)"]
    AI Reasoning [icon: sparkles, color: orange, label: "ai_reasoning/ — Stages 1,10 only (Phase 5)"]
  }

  Domain Kernel [icon: box, color: green, label: "domain/ — frozen Pydantic types, imports nothing"]
  Repositories [icon: database, color: green, label: "repositories/ — user reads + ALL writes"]
}

Supabase [icon: postgres, label: "Supabase Postgres (schema v1.1, RLS)"] {
  Catalog Tables [icon: layers, label: "cards, currencies, links, rules, milestones, award charts"]
  User Tables [icon: users, label: "user_goals, user_cards, spend profiles"]
  Result Tables [icon: file-text, label: "simulation_results + recommendation_outputs (+lineage)"]
}

Seed YAML [icon: file-text, color: green, label: "seeds/catalog/*.yaml — 9 cards, source + verified_on per row, human-reviewed"]
validate_catalog [icon: shield, color: green, label: "validate_catalog() — CI + load-time invariants"]
LLM Provider [icon: cloud, color: gray, label: "OpenAI / Gemini (one config setting)"]

// Frontend → API (Phase 7)
Landing Page > Goals API
Goal Simulator > Simulations API

// API → orchestrator → engines
Goals API > Pipeline Orchestrator
Recommendation API > Pipeline Orchestrator
Simulations API > Pipeline Orchestrator
Pipeline Orchestrator > Knowledge Engine
Pipeline Orchestrator > Valuation Engine
Pipeline Orchestrator > Optimization Engine
Pipeline Orchestrator > Simulation Engine
Pipeline Orchestrator > AI Reasoning

// The only DB touchpoints
Knowledge Engine > Catalog Tables: sole reader
Repositories > User Tables
Repositories > Result Tables: writes with lineage
Pipeline Orchestrator > Repositories

// The only LLM touchpoint
AI Reasoning > LLM Provider: intent + narration only

// Seeds are config, not code
Seed YAML > validate_catalog
validate_catalog > Catalog Tables: load_to_db.py after human review

// Sanctioned intra-engine exception: pure math reuse
Simulation Engine > Valuation Engine: transfer_math only
Optimization Engine > Valuation Engine: pure re-valuation only
```

---

## 2. The 11-stage pipeline — one request, deterministic core

LLM touches exactly two stages (1 and 10), both validated; Stages 2–9 and 11 are
deterministic and byte-replayable from a versioned catalog snapshot. Stage 8 runs
**before** ranking so Stage 9 scores simulated outcomes, not generator optimism.

```eraser
// OptiMiles — Execution Pipeline (system-execution-flow-v1.1)

User [icon: user]

LLM Stages [color: orange] {
  S1 Intent Extraction [icon: sparkles, label: "1. extract_intent() — LLM, re-validated"]
  S10 Narration [icon: message-circle, label: "10. narrate() — LLM, number-echo checked, template fallback"]
}

Deterministic Core {
  S2 Goal Resolution [icon: map-pin, color: green, label: "2. city→region, ambiguous→clarify, unknown→UnsupportedRoute"]
  S3 Requirement [icon: target, color: green, label: "3. locked award-chart row × pax + buffer (ceils UP)"]
  S4 Planning Context [icon: lock, color: green, label: "4. frozen snapshot: wallet + spend + catalog version"]
  S5 Opportunities [icon: search, color: green, label: "5. one per eligible card × category, cap-blended rate"]
  S6 Feasibility [icon: check-circle, color: orange, label: "6. PortfolioAssessment, infeasible→adjustment options"]
  S7 Strategy Generation [icon: layers, color: orange, label: "7. 3-8 archetype candidates, greedy allocation"]
  S8 Simulation [icon: clock, color: green, label: "8. monthly ledger per candidate — cap truth, transfer delays"]
  S9 Ranking [icon: bar-chart, color: orange, label: "9. prune → hard rules → weighted score from config"]
  S11 Assembly [icon: package, color: gray, label: "11. Recommendation Package, persisted with lineage"]
}

User > S1 Intent Extraction: goal in plain language
S1 Intent Extraction > S2 Goal Resolution: validated intent
S2 Goal Resolution > S3 Requirement
S3 Requirement > S4 Planning Context
S4 Planning Context > S5 Opportunities
S5 Opportunities > S6 Feasibility
S6 Feasibility > S7 Strategy Generation: feasible only
S7 Strategy Generation > S8 Simulation: per candidate
S8 Simulation > S9 Ranking: ranking scores SIMULATED outcomes
S9 Ranking > S10 Narration: headline differentiators
S10 Narration > S11 Assembly
S11 Assembly > User: structured first, narration second
```

---

## 3. Catalog data model — who transfers to whom (2026-07-04)

Transfer links belong to **currencies, not cards** (decision D-1): a card's transfer
power = card → its currency → the currency's links. This is why Infinia and Diners
Black share one entitlement, and why SBI Cashback having zero links makes it the
deliberate negative case.

```eraser
// OptiMiles — Catalog: 9 cards → 7 currencies → 14 links → 4 programs

HDFC Premium Tier [color: green] {
  Infinia [icon: credit-card, label: "Infinia — travel 16.65/100 (cap 1.5L/mo)"]
  Diners Black [icon: credit-card, label: "DCB — +10k RP per 4L quarterly"]
  HDFC RP Premium [icon: coins, label: "HDFC Reward Points (premium tier)"]
}

HDFC Regalia Tier [color: green] {
  Regalia Gold [icon: credit-card, label: "Regalia Gold — 2.67/100"]
  HDFC RP Regalia [icon: coins]
}

HSBC [color: green] {
  TravelOne [icon: credit-card, label: "TravelOne — travel 4/100, base 2/100, uncapped"]
  HSBC Points [icon: coins]
}

Axis [color: green] {
  Atlas [icon: credit-card, label: "Atlas — travel 5/100 (cap 2L/mo), DISCONTINUED for new applicants"]
  EDGE Miles [icon: coins]
  Magnus Burgundy [icon: credit-card, label: "Magnus Burgundy — Travel EDGE 30/100 (cap 2L/mo)"]
  EDGE Rewards [icon: coins]
}

Amex [color: green] {
  Platinum Travel [icon: credit-card, label: "Plat Travel — milestones 1.9L→15k, 4L→25k"]
  Platinum Charge [icon: credit-card, label: "Plat Charge — 2.5/100, fee 66k"]
  Membership Rewards [icon: coins]
}

SBI [color: red] {
  SBI Cashback [icon: credit-card, label: "Cashback — NO transfer links, deliberate negative case"]
  Cashback INR [icon: coins]
}

Airline Programs {
  KrisFlyer [icon: send, label: "KrisFlyer — PRIMARY. SIN business saver: 45,000 miles/pax"]
  Maharaja Club [icon: send, label: "Air India Maharaja Club (secondary)"]
}

Hotel Programs {
  Marriott Bonvoy [icon: home]
  Accor ALL [icon: home]
}

// card → its currency
Infinia > HDFC RP Premium
Diners Black > HDFC RP Premium
Regalia Gold > HDFC RP Regalia
TravelOne > HSBC Points
Atlas > EDGE Miles
Magnus Burgundy > EDGE Rewards
Platinum Travel > Membership Rewards
Platinum Charge > Membership Rewards
SBI Cashback > Cashback INR

// currency → program (ratio, constraints)
HDFC RP Premium > KrisFlyer: 1:1, 7-10 days
HDFC RP Premium > Maharaja Club: 2:1
HDFC RP Premium > Marriott Bonvoy: 2:1
HDFC RP Premium > Accor ALL: 2:1
HDFC RP Regalia > KrisFlyer: 2:1
HDFC RP Regalia > Marriott Bonvoy: 100:33
HDFC RP Regalia > Accor ALL: 2:1
HSBC Points > KrisFlyer: 1:1, near-instant
HSBC Points > Marriott Bonvoy: 1:1
HSBC Points > Accor ALL: 1:1
EDGE Miles > KrisFlyer: 1:2, 30k/yr cap, fee 235
EDGE Rewards > KrisFlyer: 5:4, 2L/yr cap, fee 235
Membership Rewards > KrisFlyer: 2:1
Membership Rewards > Marriott Bonvoy: 1:1
```

> Note the deliberate absences: no Axis→hotel links (Axis removed Marriott/Accor on
> 2026-04-02), no Amex→Accor (not an MR India partner), no SBI links at all.

---

## 4. Where the logic lives — reading map

| Question | Read |
|---|---|
| What are we building, for whom | `docs/prd/mvp-scope-v2.md` |
| The 11 stages, inputs/outputs, failure modes | `docs/architecture/system-execution-flow-v1.md` |
| Build order, D-1…D-7 decisions, schema v1.1 | `docs/architecture/backend-build-plan-v1.md` |
| Vocabulary (transfer ratio vs conversion, etc.) | `docs/architecture/core-domain-model-v1.md` |
| How the business thinks (engine ownership) | `docs/architecture/Product_intelligence.md` |
| Why each numeric/semantic choice was made | `docs/decisions/` — chronological, one file per decision |
| What's done / next right now | `docs/tracker.md` |

Key decision-log entries so far (chronological):
`2026-07-04-phase1-knowledge-engine-and-seed-catalog.md` (currency-split D-1 pattern, seed policy) ·
`2026-07-04-phase2-valuation-engine-math-contract.md` (exact arithmetic, rounding directions, fee/cap deviations) ·
`2026-07-04-phase3-simulation-engine-semantics.md` (month ticks, milestone periods, whole-block transfers, BR-05/06 guard) ·
`2026-07-04-catalog-expansion-and-web-verification.md` (Burgundy/Plat Charge/hotels, corrected award chart & ratios).
