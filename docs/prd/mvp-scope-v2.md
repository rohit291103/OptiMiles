# OptiMiles MVP Scope v2

**Document Path:** `/docs/prd/mvp-scope-v2.md`
**Version:** v2.0
**Status:** Approved for MVP — **canonical scope document** (supersedes `mvp_scope_1.md`)
**Source:** Mirrored from Notion "OptiMiles MVP Scope v2" (2026-06-28), reconciled against the built product and repo docs on 2026-07-03.

> **What changed from v1:** airline support narrowed to KrisFlyer + Air India Maharaja Club (Emirates/Qatar/Vistara dropped from MVP; Vistara merged into Air India, "Flying Returns" is now "Maharaja Club"); ICICI Rewards dropped from supported reward programs; primary-user definition added (₹50k–₹2L/month); "Maximize Existing Cards First" elevated to a scope principle; six core capabilities defined (adds Existing Portfolio Optimization); non-functional requirements added (30s strategy generation, config-over-code extensibility). The 8-card universe and Singapore/London/New York routes carry over from the v1 reconciliation unchanged.

---

# Purpose

This document defines the exact scope of the first OptiMiles release.

It translates the product vision and the [OptiMiles Constitution](optimiles-constitution-v1.md) into a concrete, buildable product with clearly defined capabilities, supported ecosystems, technical boundaries, and success criteria.

Anything not explicitly included in this document should be considered **out of scope for the MVP**.

---

# MVP Objective

Build a goal-based travel reward optimization platform that helps Indian users maximize the value of every rupee they spend and achieve aspirational travel goals through structured reward intelligence, optimization, simulation, and explainable recommendations.

The MVP is intentionally **narrow but deep**. Its purpose is not to support every credit card or travel program, but to deliver the most trustworthy and explainable reward strategy for a carefully curated ecosystem.

---

# Product Philosophy

The MVP follows the principles defined in the OptiMiles Constitution.

## Goal First
Every recommendation begins with a travel objective. Not with a credit card.

## Optimization Over Comparison
OptiMiles does not answer *"Which credit card is best?"* It answers *"What is the best strategy to achieve your travel goal?"*

## Maximize Existing Cards First
Before recommending additional cards, the system should extract maximum value from the user's existing portfolio.

## Rules Before AI
Reward calculations must come from deterministic logic and structured reward data. AI is responsible only for: understanding intent, orchestrating workflows, generating explanations, summarizing strategies.

## Trust Over Breadth
Supporting fewer cards with highly accurate calculations is more valuable than supporting many cards with incomplete logic.

---

# Primary User

The initial MVP is designed for users who:

- are based in India
- actively use credit cards
- spend approximately ₹50,000–₹2,00,000 per month
- are interested in premium travel rather than cashback
- are willing to plan travel months in advance
- want to maximize existing cards before applying for new ones

(Persona detail: see [user-personas-v1.md](../research/user-personas-v1.md) — primary persona is **The Travel Aspirant**.)

---

# Primary User Journey

Every user journey follows the same flow:

```
Travel Goal
    ↓
Goal Understanding
    ↓
Reward Requirement Estimation
    ↓
Current Card Analysis
    ↓
Optimization Strategy
    ↓
Spend Allocation
    ↓
Simulation
    ↓
Explainable Recommendation
```

This journey defines the product. Its backend realization is the 11-stage pipeline in [system-execution-flow-v1.md](../architecture/system-execution-flow-v1.md).

---

# Supported Goal Types

The MVP supports travel reward goals only.

## Flight Redemptions *(surfaced in product)*

Examples: Singapore Airlines Business Class, Air India Business Class.

Initial destinations:

- Singapore
- London
- New York

> **Implementation note (carried from v1 reconciliation):** the landing-page simulator wires exactly these three destinations as a static mock. Dubai remains a candidate route, not wired.

## Hotel Redemptions *(supported in the reward engine, not yet surfaced)*

Initial programs: Marriott Bonvoy, Accor Live Limitless.

Hotel planning is part of the MVP ecosystem but will evolve incrementally.

## Lifestyle Rewards *(secondary)*

Initial support: airport lounge optimization, travel benefit planning. Secondary to flight and hotel goals.

---

# Supported Reward Ecosystem

## Credit Cards — exactly eight manually validated cards

- HDFC Infinia
- HDFC Diners Club Black
- HDFC Regalia Gold
- HSBC TravelOne
- Axis Atlas
- Axis Magnus
- American Express Platinum Travel
- SBI Cashback

These cards provide sufficient ecosystem coverage while keeping reward modeling maintainable. This list is the single source of truth and matches root `CLAUDE.md` → "Initial Supported Cards."

> **UI note (carried from v1):** the landing page shows a 5-card illustrative wallet (Infinia, Diners Black, Regalia Gold, HSBC TravelOne, Amex Platinum Travel) — a deliberate visual subset, not the full scope.

> **Deferred (post-MVP candidates, carried from v1):** Amex MRCC, Amex Gold Charge, Axis Select, IDFC First Wealth, Yes Marquee, AU Zenith+, Air India SBI Signature, Vistara IDFC, Vistara SBI Prime.

## Airlines

- Singapore Airlines **KrisFlyer** *(primary focus)*
- Air India **Maharaja Club**

> **Changed from v1:** Emirates Skywards, Qatar Privilege Club, and Vistara CV Points are out of MVP scope (Vistara has merged into Air India; "Flying Returns" was renamed "Maharaja Club"). They remain schema-compatible future additions — pure data rows, no code change (see db-schema-v1 §8).

## Hotel Partners

- Marriott Bonvoy
- Accor Live Limitless

## Bank Reward Programs

- HDFC Reward Points
- Axis Edge Rewards
- American Express Membership Rewards
- SBI Reward Points

> **Changed from v1:** ICICI Rewards dropped (no ICICI card in the 8-card universe).

Only supported transfer relationships are modeled.

---

# Core Product Capabilities

The MVP focuses on six capabilities.

## 1. Goal Understanding
Understand the user's desired travel outcome. Inputs: destination, cabin class, travel timeline, monthly spend, existing cards.

## 2. Reward Intelligence
Determine: reward requirement, transfer partner, redemption estimate, transfer ratios. Powered entirely by structured reward data.

## 3. Reward Optimization
Recommend: optimal card portfolio, spend allocation, transfer strategy. Optimization considers: reward rates, category bonuses, milestones, reward caps, exclusions.

## 4. Reward Simulation
Project: monthly accumulation, milestone completion, projected redemption date, readiness confidence.

## 5. Explainable Recommendations
Every recommendation must explain: why this strategy, why these cards, why this transfer partner, expected trade-offs, assumptions made.

## 6. Existing Portfolio Optimization
Before suggesting new cards, analyze: unused benefits, transfer opportunities, spend inefficiencies, milestone opportunities.

---

# Core System Components

The MVP consists of five primary backend systems (canonical decomposition — see [system-execution-flow-v1.md](../architecture/system-execution-flow-v1.md) §0.3 for how in-flight engine designs map onto these five):

| Engine | Responsibility |
|---|---|
| **Reward Knowledge Engine** | Cards, reward rules, transfer partners, reward caps, milestones, exclusions — single source of truth. Spec: [reward-knowledge-engine-spec-v1.md](../architecture/reward-knowledge-engine-spec-v1.md) |
| **Valuation Engine** | Reward values, transfer values, redemption values; opportunity enumeration. |
| **Optimization Engine** | Spend routing, card strategy generation, transfer recommendations, feasibility, ranking. Spec: [optimization-engine-spec-v1.md](../architecture/optimization-engine-spec-v1.md) |
| **Simulation Engine** | Reward accumulation projection, milestone achievement, goal completion timeline. |
| **AI Reasoning Layer** | Goal extraction, explanation, recommendation narration, natural-language interaction. **Never performs calculations.** |

---

# MVP Assumptions

- Users manually enter spending.
- Users manually select current cards.
- Reward rules are manually maintained.
- Transfer ratios are version controlled.
- Calculations are deterministic.
- AI explains decisions but never generates reward logic.

---

# Explicitly Out of Scope

## Financial Management
budgeting · expense tracking · statement parsing · bank integrations

## Advanced Reward Features
real-time award availability · automated transfer execution · cashback optimization · dynamic fare tracking · forex optimization

## Platform Features
mobile applications · community · referrals · enterprise accounts · social features

## AI Features
autonomous agents · memory-heavy personalization · conversational copilots · autonomous financial advice

---

# Non-Functional Requirements

| Requirement | Target |
|---|---|
| **Performance** | Strategy generation completes within **30 seconds** (v1 allowed 30–60s; v2 tightens the target — LLM narration latency is the dominant cost; the deterministic core is milliseconds. The execution blueprint's streaming lever — structured results first, narration second — is the path if the budget is threatened). |
| **Accuracy** | Reward calculations must be deterministic and reproducible. |
| **Explainability** | Every recommendation must include reasoning. |
| **Maintainability** | Reward rules configurable without modifying application logic. |
| **Extensibility** | New cards, airlines, and hotel partners introduced primarily through configuration (catalog data), not code changes. |

---

# Success Criteria

The MVP succeeds when a user can:

- define a travel goal
- understand how many rewards are required
- receive an optimized reward strategy
- understand why the recommendation was made
- estimate when the goal becomes achievable

without needing expert knowledge of reward programs.

---

# MVP Boundaries

The first release intentionally prioritizes:

- depth over breadth
- trust over hype
- optimization over comparison
- deterministic systems over AI reasoning
- structured reward intelligence over content generation

The objective is not to become the largest reward platform. The objective is to become the most trusted reward optimization platform for Indian travelers.
