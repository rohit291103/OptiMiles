# Staged research data

Structured, machine-readable data captured from research but **deliberately kept
out of the seed pipeline**. Nothing in this folder is loaded by anything.

Purpose: everything here feeds **spend-routing strategy** — which card to use for
which spend, where the points can go, and what they're worth. It was captured
ahead of being usable so that when scope expands, it's a lift rather than a
re-research job.

---

## Why these are staged rather than seeded

| File | Blocked on |
|---|---|
| [`accor-outbound-transfers.yaml`](./accor-outbound-transfers.yaml) | Schema models `currency → partner` single-hop only. These are `partner → partner` rows. Multi-hop is confirmed FUTURE, not MVP (user, 2026-08-10). |
| [`staged-cards.yaml`](./staged-cards.yaml) | All four cards are outside the MVP nine. Root CLAUDE.md excludes "every Indian credit card". |

Both files mirror their `backend/seeds/catalog/` counterparts' schemas
(`ratio_from`/`ratio_to`, `earn_rate`, `monthly_cap_inr`, `source`,
`verified_on`, `needs_verification`) so promotion is mostly a copy.

---

## What's here

### `accor-outbound-transfers.yaml`
9 Accor ALL → airline ratios, **all verified against Accor's own published
conditions** on 2026-08-10. Plus the **Avios cluster topology** — Avios is one
currency across BA / Iberia / Qatar / Finnair / Aer Lingus, moving free at 1:1,
but **British Airways is the hub** and Qatar/Finnair are only reachable through
it. A naive fully-connected path model would invent routes that don't exist.

Also carries the agreed **Accor point value of ₹2.00** under `meta` — a working
calculation figure, *not* a guaranteed floor (Accor redemption is dynamic).

Headline: the modeled direct link `accor-all → qatar 2:1` is **half as good** as
the real route `accor-all → iberia 1:1 → (BA) → qatar`. Worked example is in the
file.

### `staged-cards.yaml`
Category earn rates, fees and caps for 4 non-MVP cards: **HSBC Live+**, **SBI
PhonePe Select Black**, **Axis Horizon**, **HDFC BizBlack**.

Two of them are cheap to add when the time comes, because they reuse
already-seeded currencies:
- **HDFC BizBlack** → `hdfc-rp-premium` (inherits the full HDFC transfer entitlement)
- **Axis Horizon** → `axis-edge-miles`

Its most useful entry for strategy work is BizBlack's **tax-payments category at
16.67%** — tax spend normally earns zero on Indian cards, so if it holds it's a
genuinely unusual routing option.

---

## Reliability, honestly stated

Not all of this is equally trustworthy. Ranked:

1. **Accor outbound ratios** — verified against Accor's own site. Trust these.
2. **Avios cluster mechanics** — corroborated across three independent guides.
3. **HSBC Live+** — fee, rates and the ₹1,200/cycle cap verified; the cap
   confirmed to support the claimed break-even.
4. **All arithmetic in the fee-recovery infographics** — 14 figures independently
   recomputed, all correct.
5. **Everything else in `staged-cards.yaml`** — publisher's claims, unverified
   inputs. Treat accelerated rates as **upper bounds**, since only Live+ has a
   confirmed cap.

The biggest systematic gap is **caps**. An uncapped accelerated rate makes a card
look arbitrarily good to an optimizer, which is the single largest source of
wrong spend-routing advice. Assume a cap exists wherever one isn't recorded.

---

## Prose companions

Narrative, sourcing and verification trails live one level up:

- [`../hdfc-transfer-partner-infographics-v1.md`](../hdfc-transfer-partner-infographics-v1.md) — HDFC → programs (inbound)
- [`../accor-outbound-transfer-partners-v1.md`](../accor-outbound-transfer-partners-v1.md) — Accor → airlines (outbound), the three "hacks" fact-checked
- [`../fee-recovery-card-infographics-v1.md`](../fee-recovery-card-infographics-v1.md) — the four cards, arithmetic check

---

## Open questions worth answering before promoting anything

1. **Caps** for PhonePe's 10% band, Axis Horizon Travel EDGE, and every BizBlack
   accelerated category. BizBlack's claimed 33.3% on hotels is the least
   plausible number in either file.
2. **Fee waiver thresholds** for PhonePe Select Black, Horizon and BizBlack
   (Live+ is known: ₹2L annual spend).
3. **Qantas from India** — can an India-registered ALL account convert to Qantas
   at all? Sources conflict; the row is flagged `needs_verification: true`.
4. **`1 RP = ₹1` and `1 EDGE Mile = ₹1`** — flat publisher assumptions. EDGE
   Miles in particular moved with the Apr-2026 devaluation already recorded in
   `transfer_links.yaml`.
5. **~20 unchecked Accor airline partners** — Emirates, Cathay, Etihad and IndiGo
   BluChip matter most for an India-focused product.
