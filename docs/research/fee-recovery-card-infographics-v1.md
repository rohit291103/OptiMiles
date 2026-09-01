# Fee-Recovery Infographics — Four Non-MVP Cards (v1)

**Captured:** 2026-08-10
**Status:** ✅ arithmetic independently verified · ⚠️ input rates largely unverified
**Publisher:** **CreditCardTalks** (watermarked on all four — unlike the earlier
infographic batches, this set is at least attributable). Undated.

**Companion docs:**
[`hdfc-transfer-partner-infographics-v1.md`](./hdfc-transfer-partner-infographics-v1.md) ·
[`accor-outbound-transfer-partners-v1.md`](./accor-outbound-transfer-partners-v1.md)

---

## 0. Scope warning — none of these are MVP cards

The four cards here (HSBC Live+, SBI PhonePe Select Black, Axis Horizon, HDFC
BizBlack) are **all outside the nine seeded in `cards.yaml`**. `mvp-scope-v2.md`
and root CLAUDE.md explicitly exclude "every Indian credit card" from the MVP.

This is **backlog research**, not a seeding candidate. Filed so the data exists
when card coverage expands.

---

## 1. The four cards, as claimed

### HSBC Live+
| | |
|---|---|
| Annual fee | ₹999 + GST = **₹1,179** |
| Dining + grocery + food delivery | 10% cashback → break-even at **₹11.8K** spend |
| Other eligible spends | 1.5% cashback → break-even at **₹78.6K** spend |

### SBI PhonePe Select Black
| | |
|---|---|
| Annual fee | ₹1,499 + GST = **₹1,769** |
| PhonePe spends | 10% gross − 1.18% convenience fee = **8.82% net** → **₹20.1K** |
| Online spends | 5% → **₹35.4K** |
| Stated assumption | 1 RP = ₹1; PhonePe route shown after assumed 1% convenience fee + GST |

### Axis Horizon
| | |
|---|---|
| Annual fee | ₹3,000 + GST = **₹3,540** |
| Travel route | 5 EDGE Miles/₹100 @ ₹1/mile = 5% → **₹70.8K** |
| Base route | 2 EDGE Miles/₹100 @ ₹1/mile = 2% → **₹1.77L** |

### HDFC BizBlack
| | |
|---|---|
| Annual fee | ₹10,000 + GST = **₹11,800** |
| Point value | 1 RP = ₹1 · Base 5 RP/₹150 (3.33%) |
| Tax payments | 5X = 25 RP/₹150 → 16.7% → **₹70.8K** |
| Hotels | 10X = 50 RP/₹150 → 33.3% → **₹35.4K** |
| Flights | 5X = 25 RP/₹150 → 16.7% → **₹70.8K** |
| Vouchers | 3X = 15 RP/₹150 → 10% → **₹1.18L** |

---

## 2. Independent arithmetic check — all four pass

Every figure recomputed from the stated inputs. GST assumed 18% throughout.

| Claim | Recomputed | ✓ |
|---|---|---|
| Live+ fee ₹999 → ₹1,179 | 999 × 1.18 = 1,178.82 | ✅ |
| Live+ 10% route ₹11.8K | 1,179 ÷ 0.10 = 11,790 | ✅ |
| Live+ 1.5% route ₹78.6K | 1,179 ÷ 0.015 = 78,600 | ✅ |
| PhonePe fee ₹1,499 → ₹1,769 | 1,499 × 1.18 = 1,768.82 | ✅ |
| PhonePe net 8.82% | 10 − 1.18 = 8.82 | ✅ |
| PhonePe route ₹20.1K | 1,769 ÷ 0.0882 = 20,056 | ✅ |
| PhonePe online ₹35.4K | 1,769 ÷ 0.05 = 35,380 | ✅ |
| Horizon fee ₹3,000 → ₹3,540 | 3,000 × 1.18 = 3,540 | ✅ |
| Horizon travel ₹70.8K | 3,540 ÷ 0.05 = 70,800 | ✅ |
| Horizon base ₹1.77L | 3,540 ÷ 0.02 = 177,000 | ✅ |
| BizBlack fee ₹10,000 → ₹11,800 | 10,000 × 1.18 = 11,800 | ✅ |
| BizBlack tax/flights 16.7% → ₹70.8K | 25/150 = 16.67%; 11,800 ÷ 0.1667 = 70,800 | ✅ |
| BizBlack hotels 33.3% → ₹35.4K | 50/150 = 33.33%; 11,800 ÷ 0.3333 = 35,400 | ✅ |
| BizBlack vouchers 10% → ₹1.18L | 15/150 = 10%; 11,800 ÷ 0.10 = 118,000 | ✅ |

**The arithmetic is sound.** What remains unverified is the *inputs* — earn
rates, point values, convenience fees — and, more importantly, what the
arithmetic leaves out (§3).

---

## 3. The methodological gap: caps

Every one of these calculations divides the fee by a headline rate and stops.
Real accelerated categories carry **monthly caps**, and a capped rate can make a
break-even figure unreachable no matter how much is spent. All four cards
footnote "caps apply" while the headline numbers ignore them.

### HSBC Live+ — checked, and it survives

The 10% category is capped at **₹1,200 per statement cycle** (≈ ₹12,000 of
accelerated spend/month).

Required cashback is ₹1,179, which needs ₹11,790 of category spend — **₹1,179 <
₹1,200 cap**. So the claim holds, with roughly 2% headroom, achievable inside a
single statement cycle. Tight, but correct.

**Two things the Live+ card omits, both material:**

1. **The annual fee is waived on ₹2,00,000 of annual spend.** For most holders
   this is the actual fee-recovery mechanism, and it is absent entirely.
2. As of **26 July 2026** the 10% band reportedly widened to include utilities
   and shopping (excluding Amazon, Flipkart, Myntra) under the *same* shared
   ₹1,200 cap. The infographic lists only dining/grocery/food-delivery, so it
   likely predates that change — conservative rather than wrong.

### Not yet checked

Cap structures for **SBI PhonePe Select Black** (10% band), **Axis Horizon**
(Travel EDGE 5 EM/₹100) and **HDFC BizBlack** (10X hotels via SmartBuy). BizBlack
is the one to check hardest: a 33.3% effective rate is extraordinary and almost
certainly carries a tight cap, which would make the "₹35.4K recovers ₹11,800"
claim the least reliable number in the set.

---

## 4. "Fee recovery" is the publisher's framing, not ours

**Not a domain-modeling proposal.** "Fee recovery spend" is simply how
CreditCardTalks labels these cards; it is recorded here so the numbers in §1 are
readable, and it carries **no claim on OptiMILES vocabulary**. These images were
supplied for their card data, nothing more (user, 2026-08-10).

For reference only, the quantity they compute is:

```
fee_recovery_spend = (annual_fee × (1 + gst)) ÷ effective_reward_rate
```

One factual observation worth keeping, because it is a property of the *cards*
rather than of any terminology: a **fee waiver threshold** (Live+ at ₹2L annual
spend) is a different mechanism from reward-based recovery, and the two give
different answers. Whichever way this is ever modeled, capturing only one of the
two would understate how easily a fee is offset.

---

## 5. Verification checklist

1. **Caps** for the PhonePe 10% band, Axis Horizon Travel EDGE, and BizBlack 10X
   hotels — highest priority; BizBlack's 33.3% is the least plausible figure here.
2. **Fee-waiver thresholds** for all four. Live+ is ₹2L; the other three are
   unstated on the cards and are likely the dominant recovery route.
3. **SBI PhonePe convenience fee** — the 1.18% is explicitly flagged as *assumed*
   by the publisher, not observed.
4. **1 RP = ₹1 and 1 EDGE Mile = ₹1** — both are redemption-dependent, and the
   Axis EDGE Miles value in particular moved with the Apr-2026 devaluation
   already recorded in `transfer_links.yaml`. A ₹1 flat value is optimistic.
5. **Exclusions and MCC rules** — all four footnote them; none quantify them.
6. Confirm the **26 July 2026 Live+ category change** before using either
   category list.

Nothing here belongs in `cards.yaml` until card coverage expands beyond the MVP
nine *and* items 1–4 are resolved.

---

## Sources

- [HSBC India — Live+ product page (primary)](https://www.hsbc.co.in/credit-cards/products/live-plus/)
- [Paisabazaar — HSBC Live+ (2026-08-10)](https://www.paisabazaar.com/hsbc-bank/live-plus-credit-card/)
- [Card Maven — HSBC Live+ review 2026](https://cardmaven.in/hsbc-live-plus-credit-card-review/)
- [Magnify — HSBC Live+ review](https://magnify.club/guides/hsbc-live-plus-credit-card-review/)
- Infographics: CreditCardTalks (undated, supplied by user 2026-08-10)
