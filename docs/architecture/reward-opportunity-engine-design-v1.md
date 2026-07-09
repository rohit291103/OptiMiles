# OptiMiles — Reward Opportunity Engine Design v1

**Document ID:** ROE-001
**Version:** v1.0
**Status:** Reference (superseded module home — see reconciliation below)
**Source:** Mirrored from Notion `Reward_Opportunity_Engine_Design_v1` (created 2026-07-03) on 2026-07-04.

---

> **Reconciliation note (2026-07-04):** this document predates and describes a standalone "Reward Opportunity Engine." Per [system-execution-flow-v1.md](system-execution-flow-v1.md) §0.3 and §9 (Recommendation 1) and root `CLAUDE.md`'s five-engine boundary, this is **not** a sixth engine — it is homed as the enumeration module of the **Reward Valuation Engine**: `valuation/opportunities.py` (Stage 5, `enumerate_opportunities()`), already implemented in Phase 2. Read this doc for the opportunity taxonomy, lifecycle states, and business rules (§6, §7, §10) — those are genuinely useful reference material — but treat "the Reward Opportunity Engine" throughout as "the opportunity-enumeration responsibility inside Valuation," not a separate deployable or module boundary. Where this doc's scope (e.g. AD-02 "derived from business knowledge rather than stored," promotions/merchant opportunities, full lifecycle states) exceeds what Phase 2 actually built, that excess is **future scope**, not a gap in the current implementation — MVP's `enumerate_opportunities()` covers card × category opportunities only (§6.1–6.3 partially; no merchant/promotional/loyalty opportunities yet).

---

# 1. Purpose

## Objective

The Reward Opportunity Engine (ROE) is responsible for discovering, structuring and exposing every possible reward-earning opportunity available within the OptiMiles ecosystem.

A Reward Opportunity represents a possible method through which rewards can be earned.

The engine identifies opportunities across credit cards, merchants, reward programs, promotions, transfer campaigns and milestone programs, then exposes them as normalized business objects that can be consumed by downstream engines.

The Reward Opportunity Engine does not personalize, rank, calculate or recommend opportunities. Its responsibility ends with discovering and publishing a complete catalog of valid reward opportunities.

---

# 2. Scope

## In Scope

The engine is responsible for:

- Discovering reward opportunities
- Normalizing opportunities
- Classifying opportunities
- Associating opportunities with eligible cards
- Associating opportunities with merchants
- Associating opportunities with reward programs
- Defining eligibility conditions
- Managing opportunity lifecycle
- Publishing opportunities for downstream engines

## Out of Scope

The engine is not responsible for:

- Reward calculations
- Reward valuation
- Strategy generation
- Strategy ranking
- Recommendation generation
- Timeline simulation
- User personalization
- Spend optimization

These responsibilities belong to other engines within OptiMiles.

---

# 3. Architecture Decisions

| ID | Decision |
|---|---|
| AD-01 | A Reward Opportunity is a possible method of earning rewards. |
| AD-02 | Opportunities are derived from business knowledge rather than stored directly. |
| AD-03 | The engine discovers opportunities for the entire ecosystem, independent of individual users. |
| AD-04 | Every opportunity represents a single executable business action. |
| AD-05 | Similar opportunities are treated as separate opportunities when execution differs. |
| AD-06 | Opportunities follow a defined lifecycle. |
| AD-07 | Stackable opportunities remain independent business objects. Strategy Generation determines stacking. |
| AD-08 | Every opportunity belongs to a predefined classification. |
| AD-09 | Opportunities are exposed as normalized business objects. |
| AD-10 | Every opportunity has a unique Opportunity ID. |

---

# 4. Responsibilities

The Reward Opportunity Engine is responsible for transforming business knowledge into executable reward opportunities.

Its responsibilities include:

- Discovering opportunities from business rules
- Identifying all valid earning methods
- Building normalized opportunity objects
- Maintaining opportunity lifecycle state
- Associating opportunities with relevant business entities
- Publishing opportunities to downstream engines

The engine does not make business decisions regarding which opportunity is best.

---

# 5. Internal Model

## Definition

A Reward Opportunity is a normalized business object representing a single executable action through which a user can earn rewards.

Each opportunity must describe **what action can be performed**, **under what conditions**, and **what reward mechanism becomes available**.

## Opportunity Structure

Every Reward Opportunity contains:

| Attribute | Description |
|---|---|
| Opportunity ID | Unique identifier |
| Name | Human-readable opportunity name |
| Opportunity Type | Business classification |
| Action | Action required to utilize the opportunity |
| Source | Card, Merchant, Promotion or Loyalty Program |
| Eligible Cards | Cards capable of executing the opportunity |
| Merchant | Applicable merchant (if any) |
| Reward Currency | Currency earned |
| Reward Program | Associated loyalty program |
| Eligibility Conditions | Rules governing availability |
| Validity Period | Start and end dates |
| Spend Requirement | Minimum spend requirements |
| Constraints | Business restrictions |
| Lifecycle State | Current lifecycle stage |

## Example

```
Opportunity ID
OPP-000142

Name
Amazon Voucher Purchase via SmartBuy

Action
Purchase Amazon Gift Voucher through SmartBuy

Eligible Card
HDFC Infinia

Merchant
Amazon

Platform
SmartBuy

Reward Currency
HDFC Reward Points

Validity
Always Available

Constraints
Monthly SmartBuy limits apply
```

---

# 6. Opportunity Taxonomy

Every opportunity belongs to one primary classification.

## 6.1 Base Reward Opportunities

Standard reward earning available through normal card usage.

Examples: base card earning, default spend rewards.

## 6.2 Accelerated Reward Opportunities

Enhanced earning through specific spend categories.

Examples: dining, travel, grocery, international spend.

## 6.3 Platform Opportunities

Reward opportunities available through partner platforms.

Examples: SmartBuy, Travel Edge, Reward Multiplier, Shopping Portals.

## 6.4 Merchant Opportunities

Merchant-specific earning opportunities.

Examples: Amazon, Flipkart, Swiggy, MakeMyTrip.

## 6.5 Milestone Opportunities

Rewards unlocked after achieving predefined spending thresholds.

Examples: annual spend bonus, quarterly milestone, welcome milestone.

## 6.6 Loyalty Opportunities

Reward opportunities originating from loyalty ecosystems.

Examples: airline campaigns, hotel promotions, member-exclusive offers.

## 6.7 Transfer Opportunities

Opportunities created through reward currency transfers.

Examples: standard transfers, bonus transfer campaigns, limited-time transfer bonuses.

## 6.8 Promotional Opportunities

Temporary opportunities available for a limited period.

Examples: festival campaigns, seasonal offers, partner promotions, limited-time bonus rewards.

---

# 7. Opportunity Lifecycle

```
Business Knowledge
        │
        ▼
Opportunity Derived
        │
        ▼
Validated
        │
        ▼
Published
        │
        ▼
Consumed by Downstream Engines
        │
        ▼
Expired
        │
        ▼
Archived
```

## Lifecycle States

| State | Description |
|---|---|
| Derived | Opportunity generated from business knowledge |
| Validated | Business rules verified |
| Published | Available for downstream engines |
| Expired | No longer valid |
| Archived | Retained for historical reference |

---

# 8. Inputs

| Source | Purpose |
|---|---|
| Reward Knowledge Engine | Core business knowledge |
| Reward Rules | Reward earning logic |
| Credit Cards | Eligible products |
| Merchants | Merchant-specific opportunities |
| Promotions | Temporary campaigns |
| Milestones | Spend-based opportunities |
| Transfer Relationships | Transfer-based opportunities |
| Loyalty Programs | Airline and hotel promotions |

---

# 9. Outputs

The engine publishes a normalized Reward Opportunity Catalog containing: Reward Opportunities, Opportunity Metadata, Opportunity Classification, Eligible Cards, Reward Programs, Merchants, Eligibility Conditions, Validity Information, Business Constraints, Lifecycle State.

This catalog becomes the input for downstream product intelligence engines.

---

# 10. Business Rules

- **BR-01** Every opportunity must originate from valid business knowledge.
- **BR-02** Expired opportunities must never be published.
- **BR-03** Every opportunity must represent a single executable business action.
- **BR-04** Reward calculations must never be embedded within an opportunity.
- **BR-05** An opportunity may reference multiple eligible cards.
- **BR-06** An opportunity may reference multiple reward programs where applicable.
- **BR-07** Temporary promotions override standard opportunities only for their validity period.
- **BR-08** Merchant opportunities are optional and must only exist when supported by business knowledge.
- **BR-09** Stackable opportunities remain independent entities. The Reward Opportunity Engine does not determine whether opportunities can be combined.
- **BR-10** Every published opportunity must contain complete eligibility and constraint metadata.
- **BR-11** Every opportunity must have a unique identifier.
- **BR-12** Unknown or unverified opportunities must never be published.

---

# 11. Relationships

- **Reward Knowledge Engine** — provides the business knowledge from which opportunities are derived.
- **Strategy Generation Engine** — consumes Reward Opportunities to build candidate strategies.
- **Ranking Engine** — evaluates strategies that reference Reward Opportunities.
- **Simulation Engine** — uses opportunities to project future reward accumulation.
- **Recommendation Engine** — explains opportunities that contribute to the selected recommendation.

*(Repo mapping: "Strategy Generation Engine" and "Ranking Engine" above are `optimization/strategies.py` and `optimization/ranking.py` inside the Optimization Engine — see [optimization-engine-spec-v1.md](optimization-engine-spec-v1.md).)*

---

# 12. Failure Handling

| Scenario | Engine Behavior |
|---|---|
| Promotion expired | Remove opportunity from published catalog |
| Unknown reward rule | Do not generate opportunity |
| Missing merchant mapping | Mark opportunity invalid until resolved |
| Conflicting business rules | Flag for validation; do not publish |
| Invalid transfer campaign | Exclude transfer opportunity |
| Missing eligibility information | Suppress opportunity until validated |
| Duplicate opportunity | Merge only if business action is identical; otherwise maintain separate Opportunity IDs |

The engine prioritizes correctness over completeness. Unknown or conflicting information must never be exposed to downstream engines.

---

# 13. Assumptions

- The Reward Knowledge Engine provides validated and normalized business knowledge.
- Business rules are version-controlled.
- Opportunities are independent of individual users.
- Downstream engines are responsible for personalization.
- Every opportunity can be represented as a normalized business object.

---

# 14. Constraints

- The engine cannot create opportunities without supporting business knowledge.
- The engine cannot recommend opportunities.
- The engine cannot calculate reward values.
- The engine cannot determine optimal strategies.
- The engine cannot personalize opportunities.
- The engine must remain independent of ranking and simulation logic.

---

# 15. Future Extensions

Potential future enhancements include: personalized opportunity catalogs, location-aware opportunities, real-time merchant offers, live transfer bonus monitoring, partner API integrations, AI-assisted opportunity discovery, user behavior-based opportunity prioritization, opportunity confidence scoring, community-discovered opportunities.

---

# Engine Position within OptiMiles (as designed in source doc)

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

*Repo reality (per [system-execution-flow-v1.md](system-execution-flow-v1.md) §1): Knowledge → Valuation (incl. opportunity enumeration) → Optimization (feasibility, generation, ranking) → Simulation → AI Reasoning (narration) → Assembly. Same responsibilities, five engines instead of six — see the reconciliation note at the top of this document.*

---

# End of Specification
