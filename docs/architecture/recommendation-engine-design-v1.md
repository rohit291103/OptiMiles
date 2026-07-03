# OptiMiles — Recommendation Engine Design v1

**Document IDs consolidated:** RED-001 (`Recommendation_Engine_Design`), REW-001 (`Recommendation_Engine_Workflow_v1`), RIF-001 (`Recommendation Intelligence Framework`)
**Version:** v1.0
**Status:** Active — product-level design; the backend realization is [system-execution-flow-v1.md](system-execution-flow-v1.md)
**Source:** Mirrored and consolidated from three overlapping Notion docs (2026-06-28) on 2026-07-03. The three described the same system at three altitudes (philosophy → workflow → engine design); this repo mirror merges them and adds the reconciliation to the execution blueprint (§6).

---

# 1. Purpose

The Recommendation Engine is the core intelligence layer of OptiMiles. It transforms a user's travel goal, financial profile, and reward ecosystem into a personalized, explainable, and executable reward strategy.

Rather than recommending individual credit cards, the engine generates and evaluates multiple reward strategies before presenting the most suitable recommendation based on the user's goals, existing portfolio, spending behaviour, and personal preferences.

Existing tools primarily provide information — they compare cards, list benefits, answer isolated questions. OptiMiles solves the *decision problem*: the optimal sequence of actions to achieve a specific travel goal.

---

# 2. Design Principles

| ID | Principle | Meaning |
|---|---|---|
| DP-01 | **Goal-First Architecture** | Recommendations always begin with the travel goal; never with "the best credit card." The goal defines the optimization problem. |
| DP-02 | **Strategy Over Product Recommendation** | The output is a complete execution plan (goal assessment, portfolio analysis, accumulation strategy, spend allocation, transfer plan, timeline, action items, supporting calculations) — cards are one component. |
| DP-03 | **Existing Portfolio First** | Determine whether the current portfolio can achieve the goal before introducing new products; additions must create meaningful incremental value. |
| DP-04 | **Generate Broad, Recommend Narrow** | Internally generate the feasible strategy space; show the user one primary recommendation, with alternatives available on demand. *(MVP realization: bounded archetype generation — see §6, conflict C-2.)* |
| DP-05 | **Deterministic Business Logic** | Reward calculations, transfer ratios, milestones, eligibility, spend optimization, timeline simulation and ranking are always deterministic. LLMs only: goal understanding, follow-up questions, explanation, summaries. |
| DP-06 | **Explainability** | Every recommendation answers: why this strategy, why better than alternatives, how rewards are calculated, what assumptions were made, what to do next. |
| DP-07 | **Preference-Aware Optimization** | No universally "best" strategy. Ranking adapts to annual-fee tolerance, timeline urgency, willingness to apply for cards, complexity tolerance, spending habits. |

## Recommendation objectives (from RIF)

**Primary:** maximize likelihood of achieving the goal; minimize time to goal; maximize value from existing ecosystems; recommend only actions with meaningful incremental value; produce realistically executable strategies.

**Secondary:** reduce decision complexity; build trust through explainability; minimize unnecessary fees; adapt to preferences; provide alternatives when multiple valid paths exist.

---

# 3. Business Workflow (consolidated RED/REW phases)

```
User Goal
   ↓  1. Goal Understanding            (AI: parse goal, identify missing info)
   ↓  2. User Context Collection       (profile, cards, balances, spending, constraints)
   ↓  3. Reward Requirement Analysis   (target program, miles needed, taxes, transfer ecosystems)
   ↓  4. Portfolio Analysis            (current capability, strengths, reward gap, initial feasibility)
   ↓  5. Reward Opportunity Discovery  (earning paths, accelerators, milestones, transfer paths)
   ↓  6. Strategy Generation           (existing-portfolio first; expand only if justified)
   ↓  7. Strategy Validation           (eligibility, transfer paths, calculations, spending assumptions)
   ↓  8. Strategy Pruning              (remove dominated / low-value strategies)
   ↓  9. Strategy Ranking              (preference-aware scoring; select primary + alternatives)
   ↓ 10. Recommendation Packaging      (explainable package: summary, reasoning, actions, alternatives)
User
```

## Key decision points

| Decision | Outcomes |
|---|---|
| Is the travel goal complete? | Continue / ask follow-up questions |
| Is the user profile complete? | Continue / request additional information |
| Can the current portfolio achieve the goal? | Existing-portfolio strategy / expanded strategy search |
| Are additional cards required? | Yes / No |
| Are generated strategies valid? | Keep / remove |
| Which strategy provides the highest user value? | Highest-ranked selected as primary |

---

# 4. AI vs Deterministic Responsibilities

| Capability | AI | Deterministic |
|---|---|---|
| Goal understanding / follow-up questions / intent extraction | ✅ | |
| Reward calculations / valuation / transfer logic / eligibility | | ✅ |
| Reward opportunity discovery | | ✅ |
| Strategy generation | | ✅ *(see §6 conflict C-1 — the Notion draft's "AI-assisted" marker is resolved to fully deterministic)* |
| Strategy validation / pruning / ranking | | ✅ |
| Recommendation explanation / summary | ✅ | |

---

# 5. The Recommendation Package

The engine outputs a structured **Recommendation Package**, not a card suggestion:

- Goal Summary · Goal Feasibility Assessment · Required Reward Currency
- Current Portfolio Assessment · Reward Gap Analysis
- Recommended Strategy · Spend Allocation Plan · Reward Opportunity Breakdown · Transfer Plan
- Timeline Projection · Expected Reward Accumulation · Estimated Time to Goal
- Strategy Score · Supporting Calculations · Key Assumptions · Risks & Limitations
- Recommended Next Actions · Alternative Strategies

---

# 6. Reconciliation with the Execution Blueprint (added in repo mirror)

The business workflow above (§3) and the backend pipeline in [system-execution-flow-v1.md](system-execution-flow-v1.md) describe the same system. Mapping and resolved conflicts:

## 6.1 Phase → Stage mapping

| Business phase (this doc) | Blueprint stage(s) | Notes |
|---|---|---|
| 1. Goal Understanding | Stage 1 (Intent Extraction & Clarification) + Stage 2 (validation) | Blueprint splits LLM proposal from deterministic catalog validation — the trust boundary. |
| 2. User Context Collection | Stage 4 (Planning Context Assembly) + the UX Goal Discovery flow | Collection is UX; assembly is backend. |
| 3. Reward Requirement Analysis | Stages 2–3 (Goal Resolution + Requirement Estimation) | |
| 4. Portfolio Analysis | Stages 4–6 (context, opportunity aggregates, feasibility gate) | Blueprint v1.1 makes the Portfolio Assessment / reward gap an explicit named output of the feasibility gate. |
| 5. Reward Opportunity Discovery | Stage 5 (Opportunity Enumeration & Valuation) | `valuation/opportunities.py` per blueprint §0.3. |
| 6. Strategy Generation | Stage 7 (Candidate Strategy Generation) | Archetype-based; existing-portfolio strategy always generated first (= SGE BR-01). |
| 7. Strategy Validation | Stage 7 exit checks (blueprint v1.1 names them explicitly) | Eligibility, constraints, transfer-path validity, cap-consistency. |
| 8. Strategy Pruning | Stage 9 pre-pass (dedupe + dominance removal, blueprint v1.1) | |
| 9. Strategy Ranking | Stage 9 (Ranking & Selection) | Preference-aware weights (v1.1). |
| 10. Recommendation Packaging | Stages 10–11 (Narration + Assembly) | Package contents (§5) adopted as the `FinalRecommendation` payload contract. |
| *(not present in Notion drafts)* | **Stage 8 (Timeline Simulation)** | The Notion workflow estimated timelines *inside* generation. The blueprint simulates each candidate month-by-month as its own stage so ranking scores simulated outcomes, not generator estimates, and so the same engine powers the standalone simulator. **This is an improvement the Notion docs should adopt.** |

## 6.2 Resolved conflicts

| # | Conflict | Resolution |
|---|---|---|
| C-1 | RED-001 §7 marked Strategy Generation "⚠️ AI-assisted" while DP-05 (same doc) lists spend optimization as always-deterministic. | **Fully deterministic.** DP-05 and the constitution's "Rules Before AI" win; an LLM proposing strategies would reintroduce the hallucination class the whole architecture exists to prevent. The table in §4 above is corrected accordingly; the Notion original should be edited to match. |
| C-2 | DP-04 / SGE BR-03 say "generate **every** feasible strategy"; the blueprint bounds generation to 3–8 archetype-derived candidates. | **Bounded archetypes stand for MVP.** "Every feasible strategy" is combinatorially unbounded (8 cards × 8 categories × milestone/transfer timing). Archetypes (status-quo-optimized, one-new-card, concentrated/milestone, simplest-viable) are the buildable realization of "generate broad, recommend narrow": they cover the *structurally distinct* strategy space, which is what ranking and explanation need. If real cases show a missed better strategy, widen archetypes or add OR-Tools behind the same interface — evidence first. |
| C-3 | Notion names three engines (Strategy Generation, Strategy Ranking, Reward Opportunity). | Per blueprint §0.3 and CLAUDE.md's five-system decomposition: Opportunity → Valuation Engine module; Generation + Ranking → Optimization Engine modules ([optimization-engine-spec-v1.md](optimization-engine-spec-v1.md)). Business responsibilities unchanged; only the module homes differ. |
| C-4 | No explicit feasibility gate in the Notion workflow (feasibility is folded into generation, D-07). | Blueprint Stage 6 stands: fail fast **before** generation, and return computed adjustment options (extend timeline / add card / downgrade cabin) instead of a least-bad strategy. This also powers the UX journey's "Goal Achievability" hero section directly. |

## 6.3 Improvements the blueprint adopted from these docs (v1.1)

1. **Preference-aware ranking (DP-07)** — a deterministic preference profile (fee tolerance, urgency, complexity tolerance, no-new-cards) collected in Goal Discovery modulates ranking weights.
2. **Explicit validation + pruning** — named steps (Stage 7 exit / Stage 9 pre-pass) rather than implicit checks.
3. **Recommendation Package contract (§5)** — adopted as the response payload shape, including Reward Gap Analysis and Risks & Limitations, which the blueprint's original `FinalRecommendation` lacked.
4. **Portfolio Assessment as a named object** — current capability + reward gap emitted by the feasibility gate, feeding both narration and the dashboard.
