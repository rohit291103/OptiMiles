# Lounge Access — Research Brief v1

**Created:** 2026-08-31 · **Updated:** 2026-08-31 (coverage 2 → 4 cards)
**For:** Gemini (Research Analyst, per `CLAUDE.md` → AI Collaboration Model), or a human reviewer
**Why this exists:** the lounge data model is built and validated; what it lacks is *data*. A research pass on 2026-08-31 found the published figures too conflicting to seed for 7 of 9 cards, so they were deliberately left uncovered rather than guessed at.

---

## The rule this brief operates under

`CLAUDE.md` → *Scope: Breadth With Depth*. Three tiers, and a card only moves up by being verified, not by being wanted:

- **Verified** — primary source (the issuer's own T&C page or PDF), `needs_verification: false`. Only this tier may feed optimization output.
- **Listed** — specific figures from a credible secondary source, `needs_verification: true`, labelled unverified in the UI.
- **Not covered** — no rows. The product says "we don't cover this card's lounge conditions yet". **This is an acceptable answer.**

Where a condition is ambiguous, seed the **more restrictive** reading. A benefit that turns out better than promised is a pleasant surprise; one that turns out worse sends someone to a lounge desk to be turned away, which is the trust failure the whole product exists to avoid.

---

## Current coverage

| Card | Status | Source |
|---|---|---|
| HDFC Infinia Metal | **Verified** | HDFC "Airport Lounge Access Program" T&C PDF, effective 2026-07-02 |
| HDFC Regalia Gold | **Listed** (needs verification) | cardexpert.in 2026 lounge-access update — specific figures, secondary source |
| HDFC Diners Club Black Metal | **Listed** (needs verification) | paisabazaar + cardexpert + 1finance reviews (2026), consistent across all three |
| HSBC TravelOne | Not covered | — |
| Axis Atlas | Not covered | — |
| Axis Magnus for Burgundy | Not covered | — |
| Amex Platinum Travel | **Listed** (needs verification) | americanexpress.com/in benefits pages — issuer primary source, but per-visit international charge unconfirmed |
| Amex Platinum Charge | Not covered | — |
| SBI Cashback | Not covered (`has_lounge_access: false` — likely correct, unconfirmed) | — |

---

## What is needed per card

For each card, for **domestic and international separately**:

1. **Programme** — Priority Pass / DreamFolks / LoungeOne / Visa / Mastercard / issuer-direct
2. **Visits and period** — the number, and the window it is counted over
3. **Reset anchor** — calendar quarter, calendar year, card anniversary, or statement cycle. **This is seeded explicitly and never assumed**; it is the likeliest source of a wrong visit count, and the schema rejects a counted allowance that does not declare one.
4. **Spend gate** — the spend, and the period it is measured in. Note these are usually measured in the *preceding* period.
5. **Guest visits** — how many are complimentary (0 is a real and common answer), and whether a guest visit consumes the cardholder's own allowance
6. **Enrollment** — must the holder activate a membership before the benefit exists?
7. **Per-visit charges** — including foreign-currency guest fees
8. **Source URL + date** — a primary issuer source wherever possible

---

## Specific conflicts found on 2026-08-31 — resolve these first

### Axis Atlas — irreconcilable, do not seed until settled
- One source: **8 domestic (Silver) / 12 (Gold) / 18 (Platinum)**, tiered on annual spend
- Another: a flat **18 domestic + 12 international**, no spend gate
- A third: **Platinum = 12 domestic + 6 international**

These cannot all be true. Note the tiers, if real, should map onto the milestone thresholds already seeded for Atlas (Silver ₹3L, Gold ₹7.5L, Platinum ₹15L annual) — the schema supports this as one row per tier, distinguished by `spend_gate_inr`.

**Also unresolved:** Axis reportedly moved Atlas international access **from DreamFolks to Priority Pass**, with **LoungeOne** taking domestic, during 2026. Confirm the current vendors before seeding, and confirm whether the LoungeOne row in `lounge_programs.yaml` is real — it is currently seeded on secondary coverage alone.

### HSBC TravelOne — searches return the wrong product
Results for "HSBC TravelOne lounge" describe HSBC's **UK** (Premier World Elite) and **Singapore** cards. The Indian TravelOne is a different product. One secondary claim — *4 visits a year via DragonPass, no guest sharing* — needs confirmation against hsbc.co.in, and DragonPass is not yet in `lounge_programs.yaml`.

### HDFC Diners Club Black Metal
The mid-2026 HDFC revision that spend-gated Regalia Gold is documented as also touching **Diners Club Privilege** and **BizPower**. Whether **Diners Club Black Metal** was affected is unconfirmed — the sources reviewed explicitly did not cover it. Given it shares the Infinia reward tier, it may share Infinia's unlimited terms, but **do not assume that**; it is exactly the kind of inference that produces a confidently wrong answer.

### Amex Platinum Travel — one open question
Seeded from Amex India's own pages: **8 domestic visits a year, capped at 2 a quarter**, ₹750 per further visit. Modelled as the **quarterly** limit, because that is what binds on any single trip.

**Open:** Priority Pass *membership* is complimentary (USD 99 fee waived) for the basic cardmember and one supplementary — but membership is not visits. International visits are seeded as **zero complimentary** pending confirmation of the per-visit charge. If visits turn out to be included, raise the count; never lower a promise already shown to a user.

### Amex Platinum Charge
Not researched. Amex India publishes its own T&Cs, so this should be reachable at the verified tier.

### HDFC Diners Club Black Metal — now seeded, still needs a primary source
Three independent secondary sources agree on **unlimited domestic and unlimited international** (1,300+ lounges, Diners Club network) for primary and add-on members, with no spend condition. Seeded on that agreement at the *listed* tier. Confirm against HDFC's own T&C — and note this is the row to re-check first if HDFC extends its 2026 spend-gating further.

---

## Where the model already handles the hard cases

Worth knowing before researching, so findings are recorded in the right shape:

- **Tiered entitlements** — one row per tier, distinguished by `spend_gate_inr`. The uniqueness constraint includes the gate for exactly this reason.
- **Unlimited vs none** — `visits_per_period = NULL` is unlimited; `0` means none are granted. Infinia uses both: unlimited cardholder access, zero complimentary guest visits (guests pay USD 27 + GST).
- **Spend gates** — `spend_gate_inr` + `spend_gate_period`, and the schema rejects one without the other, because "₹60,000" with no window is not a condition anyone can act on.
- **Anything unstructured** — per-visit charges, add-on-holder rules, foreign-currency guest fees — goes in `conditions` as prose rather than being forced into a number.
