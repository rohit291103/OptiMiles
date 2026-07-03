# OptiMiles — Reward Knowledge Engine Specification v1

**Document ID:** RKE-001
**Version:** v1.0
**Status:** Active
**Source:** Mirrored from Notion `Reward_Knowledge_Engine_Specification_v1` (2026-06-28, the newer of the two Notion RKE docs) on 2026-07-03, with a repo reconciliation section (§12) added.

---

# 1. Purpose

The Reward Knowledge Engine (RKE) is the central business knowledge repository of OptiMiles. Its purpose is to maintain accurate, structured, versioned and normalized reward intelligence that powers every recommendation, strategy, simulation and optimization performed by the platform.

The RKE does **not** make decisions or recommendations. It is the single source of truth from which all other engines retrieve reward knowledge.

---

# 2. Scope

**Responsible for:** maintaining structured reward knowledge; normalizing information from multiple sources; managing relationships between business entities; versioning business rules; exposing standardized knowledge to downstream engines.

**Not responsible for:** strategy generation, strategy ranking, recommendation generation, simulation, user personalization, reward opportunity discovery.

---

# 3. Architecture Decisions

| ID | Decision |
|---|---|
| AD-01 | Manual research is the primary source of truth. Automated scraping continuously validates and identifies changes. |
| AD-02 | Reward knowledge is stored at the lowest meaningful business-rule granularity. |
| AD-03 | Active knowledge and historical versions are maintained simultaneously. |
| AD-04 | Transfer Relationships are independent business objects. |
| AD-05 | Reward Opportunities are derived (by the Valuation Engine's opportunity module) and are not stored directly. |
| AD-06 | Merchants are first-class business entities. |

---

# 4. Responsibilities

Maintains business knowledge for: credit cards, reward currencies, reward programs, airlines, hotels, merchants, spend categories, reward rules, transfer relationships, promotions, milestones, redemption rules, eligibility rules.

---

# 5. Knowledge Architecture — three logical layers

## Layer 1 — Reference Knowledge (relatively stable)
Credit Card · Merchant · Airline · Hotel · Reward Program · Reward Currency · Spend Category

## Layer 2 — Business Rules (change over time → versioned)
Reward Rule · Transfer Relationship · Promotion · Milestone · Eligibility Rule · Redemption Rule

## Layer 3 — Derived Knowledge (never stored; computed downstream)
Reward Opportunities · best transfer paths · reward valuation · optimized earning paths

This separation keeps the knowledge engine normalized while downstream engines evolve independently.

---

# 6. Canonical Business Objects

| Object | Contains |
|---|---|
| **Credit Card** | issuer, network, annual fee, reward currency, supported reward rules, supported transfer relationships, eligibility rules, milestones |
| **Reward Currency** | name, expiry rules, supported transfer relationships. Examples: HDFC Reward Points, HSBC Reward Points, Axis EDGE Rewards, Membership Rewards |
| **Reward Program** | redemption rules, supported airlines/hotels, transfer relationships. Examples: KrisFlyer, Maharaja Club, Marriott Bonvoy, Accor Live Limitless |
| **Reward Rule** | spend category, merchant (optional), reward rate (e.g. ₹150 = 5 points), caps, conditions, effective date, expiry date. **Versioned.** |
| **Transfer Relationship** | source currency, destination program, transfer ratio, min/max transfer, transfer time, effective date, status. Independent objects, shareable across cards. |
| **Merchant** | merchant category, supported spend categories, portal relationships, promotion relationships. Examples: Amazon, Flipkart, SmartBuy, GyFTR, MakeMyTrip |
| **Promotion** | validity period, eligible cards, eligible merchants, bonus rules, conditions |
| **Milestone** | threshold, reward, conditions, validity |
| **Redemption Rule** | required reward currency, estimated points, taxes & fees, cabin class/room type, restrictions |
| **Eligibility Rule** | minimum income, existing-customer restrictions, upgrade requirements |

---

# 7. Knowledge Relationships

```
Credit Card ── Reward Currency
     ├──────── Reward Rules
     ├──────── Milestones
     └──────── Eligibility Rules

Reward Currency → Transfer Relationship → Reward Program → Redemption Rules

Merchant ── Promotion
     └───── Reward Rule
```

---

# 8. Knowledge Sources

**Manual research (primary source of truth):** official bank documentation, official airline/hotel loyalty documentation, verified product guides, internal validation.

**Automated collection (freshness):** official website monitoring, automated scraping, change detection. Detected changes are validated before becoming active knowledge.

---

# 9. Version Management

- **Active version:** the currently valid business rules used by all engines.
- **Historical versions:** every previous version retained — enables recommendation auditing, historical simulations, change tracking, rollback. Never deleted.

---

# 10. Outputs

Exposes structured knowledge for downstream consumption: credit cards, reward programs, reward rules, transfer relationships, promotions, merchants, milestones, redemption rules, eligibility rules.

Reward Opportunities are intentionally excluded — they are derived downstream (AD-05).

---

# 11. Assumptions & Constraints

- Manual research is authoritative; scraped data must be validated before activation.
- Every business rule exists in exactly one canonical location.
- Reward calculations must never duplicate business rules.
- **Unknown information must never be inferred.**
- Downstream engines consume knowledge but never modify it.

---

# 12. Repo Reconciliation (added in repo mirror, 2026-07-03)

How this spec relates to what the repo already defines:

## 12.1 Consistent with the execution blueprint

- "Single source of truth, downstream engines never modify" = the Knowledge Engine's sole-reader-of-catalog + versioned immutable snapshot in [system-execution-flow-v1.md](system-execution-flow-v1.md) §3.
- AD-05 (opportunities derived, not stored) = blueprint Stage 5 (`valuation/opportunities.py` derives `OpportunitySet` per request; nothing persisted).
- AD-03/§9 versioning = the blueprint's snapshot-version lineage on results (blueprint §9.6).
- One naming delta: this spec says opportunities are derived by a "Reward Opportunity Engine"; per blueprint §0.3 that is a **module of the Valuation Engine**, not a sixth engine. §3/AD-05 above are worded accordingly.

## 12.2 Deltas vs. `db-schema-v1.md` (decisions needed before backend build)

The current DB schema is a deliberately simpler MVP subset of this spec. Gaps, in priority order:

| # | RKE concept | db-schema-v1 today | Recommendation |
|---|---|---|---|
| 1 | **Reward Currency as first-class entity** (AD-04: transfer relationships belong to *currencies*, not cards) | `cards.points_currency` is TEXT; `card_transfer_partners` links transfers per *card* | **✅ DECIDED 2026-07-03 — adopted** (build plan D-1). DDL in [`backend-build-plan-v1.md`](backend-build-plan-v1.md) §3: `reward_currencies` table, `cards.reward_currency_id` FK, `currency_transfer_partners` junction. Rationale: HDFC Infinia/DCB/Regalia share one currency; per-card transfer rows duplicate the same ratio 3× and can drift. |
| 2 | **Rule versioning** (AD-03) | in-place updates + `is_active`; versioning listed as post-MVP (§6.2) | Keep post-MVP as schemed, but the blueprint's snapshot-version column on results (already recommended) is the minimum viable audit trail and should land in v1.1. |
| 3 | **Merchants + Promotions** (AD-06) | absent | Defer (post-MVP). Needed for portal/voucher opportunities (SmartBuy, GyFTR) — a large accuracy lever for HDFC cards, but a big data-maintenance commitment. Revisit after core engines validate against the 8-card set. |
| 4 | **Eligibility Rules** | only `cards.min_income_inr` | Sufficient for MVP (used to annotate new-card suggestions); expand only when card-acquisition advice becomes richer. |
| 5 | **Redemption Rules** | `award_charts` covers flight redemptions | Adequate; hotel redemption rows are a data addition, no schema change. |
| 6 | **Scraping/change-detection channel** (AD-01) | not modeled | MVP: manual curation + the blueprint's `validate_catalog()` invariant checks. A `catalog_change_alerts` table + Playwright monitors are post-MVP per PRD §5H ("no fully automated scraping infrastructure initially"). |

Item 1 should be decided (and if accepted, db-schema bumped to v1.1) **before** the Reward Knowledge Engine is scaffolded — it changes the engine's core types.
