---
name: domain-modeling
description: Sharpens and locks down OptiMILES reward/finance vocabulary (transfer ratio vs. conversion ratio, accrual vs. redemption, milestone vs. reward cap, valuation vs. efficiency score, etc.) so docs and code use the same words for the same concepts. Use when introducing a new domain term, when a term is used inconsistently across /docs or code, or before modeling a new reward/card/transfer concept in the schema.
---

# domain-modeling

OptiMILES lives or dies on explainability (root `CLAUDE.md`'s Guiding Principle: "trustworthy AI reward strategist"). Explainability collapses the moment two docs use the same word for different things, or two different words for the same thing. This skill exists to catch that before it reaches `docs/architecture/db-schema-v1.md` or actual code.

## When to run this

- A new reward/finance concept is about to be modeled (new card field, new transfer mechanic, new redemption type).
- You notice a term used two different ways across `docs/prd/`, `docs/architecture/`, `docs/research/`, or code.
- Before writing a schema or API contract that will outlive this conversation.

Also check `docs/tracker.md` (via the `tracker-sync` skill) — if the schema/code this term would land in doesn't exist yet per the tracker, the reconciliation step below should still pick a canonical definition, just note it's being defined ahead of implementation.

## The core distinctions to keep straight in OptiMILES

These are the terms most likely to get blurred — check new content against this list first:

| Term | Is | Is NOT |
|---|---|---|
| **Transfer ratio** | The fixed exchange rate a bank publishes for moving points to an airline/hotel partner (e.g. 5:4) | A user's *effective* redemption value (that's valuation) |
| **Accrual** | Points/miles earned from spend or a signup bonus | Points received via a transfer (that's a transfer event) |
| **Redemption** | Converting accumulated miles into the actual reward (a flight, a seat) | Transferring points between programs (that's a transfer) |
| **Milestone** | A spend threshold that unlocks a bonus (e.g. ₹15L spend → bonus miles) | A reward cap (a milestone is a bonus *trigger*; a cap is a bonus *ceiling*) |
| **Reward cap** | The maximum reward rate/value a card will pay out in a category or period | A milestone (see above) |
| **Reward valuation** | The estimated real-world value of 1 point/mile in a specific redemption (cents per point) | The face value or bank-stated worth of points |
| **Reward efficiency** | A score comparing valuation achieved vs. theoretical best for that spend | Valuation itself — efficiency is relative, valuation is absolute |
| **Spend routing** | Directing a specific purchase to the optimal card given category bonuses | Card "strategy" in general (routing is the tactical, per-transaction decision) |

## Workflow

1. **Inventory** — grep the term (and close synonyms) across `docs/` and any backend code that exists. List every place it's defined or used.
2. **Reconcile** — if usages conflict, the canonical definition wins from (in order): `docs/architecture/db-schema-v1.md` (if the term is already a schema field) → `docs/prd/mvp_scope_1.md` → root `CLAUDE.md`. If none of these define it yet, propose one definition and say so explicitly — don't silently pick one.
3. **Record** — new or clarified terms belong in `docs/architecture/db-schema-v1.md` if they map to a schema field, otherwise in a `docs/research/` glossary note. Don't invent a new `/docs` subfolder for a glossary; route per the `docs-sync` skill's Mode C.
4. **Flag, don't silently rewrite** — if you find an existing doc using a term incorrectly per this reconciliation, tell the user before changing historical research/decision docs (same rule `docs-sync` follows).

## Output shape when reporting findings

```
## Domain term check — <term>

**Canonical definition:** <definition + source doc>
**Conflicting usages found:** <file:line — what it implies instead>
**Recommendation:** <align all to canonical, or canonical needs updating because ___>
```
