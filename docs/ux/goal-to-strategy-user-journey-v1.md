# OptiMiles — Goal-to-Strategy User Journey v1

**Document Path:** `/docs/ux/goal-to-strategy-user-journey-v1.md`
**Version:** v1 · **Stage:** User Experience Definition
**Source:** Mirrored from Notion `Goal_To_Strategy_User_Journey_v1` (2026-06-28) on 2026-07-03.
**Purpose:** The complete end-to-end user experience from travel goal input to actionable reward strategy. This is the *product* journey; the backend realization of stages 3–4 is [system-execution-flow-v1.md](../architecture/system-execution-flow-v1.md). (The existing [landing-page-v1.md](landing-page-v1.md) covers the marketing site; this doc covers the logged-in product experience — most of it not yet built.)

---

# 1. Experience vision

The user does not come looking for a credit card; they come with a travel aspiration. The experience should feel like **Google Maps for travel rewards**: enter a destination, get the route.

```
Travel Goal → Feasibility Analysis → Strategy Generation → Execution Plan → Goal Achievement
```

Cards are the mechanism. Goals are the product.

# 2. Core UX principles

1. **Goal first** — never open with "which card/bank/program?"; open with *"What travel experience are you trying to achieve?"*
2. **Explain before recommending** — achievability and difficulty before card names.
3. **Strategy over comparison** — "Here is your plan," not "here are 20 cards."
4. **Progress visibility** — where I am, where I need to reach, what moves me closer.
5. **Transparency builds trust** — why this card, why this transfer path, why this strategy wins.

# 3. Journey overview

```
Landing Page → Goal Entry → Goal Discovery → Goal Analysis
→ Strategy Dashboard → Scenario Comparison → Save Plan → Track Progress
```

---

# 4. Stage 1 — Goal Entry

Primary prompt: **"What travel goal do you want to achieve?"** — natural-language input ("I want Singapore Airlines Business Class from India to Singapore in 9 months"). Backend: pipeline Stage 1 (intent extraction; structured form as fallback).

# 5. Stage 2 — Goal Discovery

Conversational, lightweight collection of what optimization needs:

| # | Question | Purpose |
|---|---|---|
| 1 | Existing credit cards | Current ecosystem access |
| 2 | Existing reward balances | Current progress |
| 3 | Monthly spend (ranges: <₹25k / ₹25–50k / ₹50k–1L / ₹1L+) | Accumulation velocity |
| 4 | Spending categories | Spend allocation optimization |
| 5 | Annual fee comfort (low / moderate / premium accepted) | Realistic recommendations — feeds the preference profile that modulates ranking weights |

# 6. Stage 3 — Goal Analysis

Visible, structured progress while the pipeline runs (reinforces trust):

```
Analyzing Goal → Estimating Reward Requirement → Evaluating Transfer Partners
→ Building Reward Strategy → Running Simulations
```

# 7. Stage 4 — Strategy Dashboard *(primary product experience)*

Must answer four questions: Can I achieve this goal? What do I need? What should I do? When will I get there?

| Section | Content | Pipeline source |
|---|---|---|
| A. Goal Summary | Goal, route, timeline, estimated requirement (e.g. 95,000 KrisFlyer miles) | `TravelGoal` + `RewardRequirement` |
| B. Goal Achievability *(hero section)* | Status (Achievable), confidence, estimated completion, progress 0→100% | `FeasibilityVerdict` + ranking confidence |
| C. Required Actions | Ordered execution steps (apply for X, route ₹50k monthly, transfer to KrisFlyer) | Recommendation Package action items |
| D. Recommended Card Strategy | Primary/secondary cards + strategy objective | Winning `CandidateStrategy` |
| E. Spend Allocation Plan | Category → card table | `SpendAllocation` |
| F. Reward Timeline | Month-by-month points, milestones, % progress, ETA | `SimulationResult` ledger |
| G. Transfer Path | Spend → points currency → miles → redemption visualization | Transfer plan |
| H. Why This Strategy? | Explainability layer (e.g. "Amex selected because milestone rewards generate a large share of required miles…") | Narration + score breakdown |

Information hierarchy (most important first): Goal Summary → Achievability → Required Actions → Strategy → Allocation → Timeline → Transfer Path → Explanation.

# 8. Stage 5 — Scenario Comparison

Alternative strategies with named trade-offs — **Strategy A: Fastest Path** · **Strategy B: Lowest Cost** · **Strategy C: Existing Cards Only**. Compare on: completion probability, timeline, total annual fees, estimated reward generation. (Maps to ranked alternates + their `headline_differentiator`.)

# 9. Stage 6 — Save & Track

Saved plans: goal, timeline, recommended cards, reward targets, simulation outputs. Return visits show progress (e.g. "42% — 38,000 / 95,000 miles — ETA February 2027").

---

# 10. MVP screen inventory

1. Landing Page *(built — see landing-page-v1.md)*
2. Goal Discovery Flow
3. Analysis Screen
4. Strategy Dashboard
5. Scenario Comparison
6. Saved Plans Dashboard

No additional screens unless they directly improve strategy quality or execution clarity.

# 11. MVP UX boundaries (not included)

Card application flows · bank integrations · expense tracking · statement imports · live reward synchronization · travel booking · award seat search · community features. OptiMiles provides the strategy; execution remains with the user.

# 12. Success criteria

Within 30–60 seconds, a user can: enter a goal → understand achievability → receive a trustworthy recommendation → understand why → leave with a clear action plan. The experience answers: *"Can I achieve my travel goal, and what is the smartest path to get there?"*
