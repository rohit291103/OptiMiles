# OptiMILES — Project Context & Engineering Constitution

## Project Name

OptiMILES

---

# Project Overview

OptiMILES is an AI-powered reward optimization and financial decision intelligence platform focused on Indian credit cards, airline miles, transfer partners, reward simulations, and goal-based travel optimization.

The platform helps users achieve premium travel and lifestyle goals through:

* intelligent reward strategy generation
* spend optimization
* transfer partner optimization
* reward accumulation simulations
* explainable AI recommendations

Example user goals — **plural, deliberately** (amended 2026-08-26, see *Scope: Breadth With Depth* below):

> “I want to fly Singapore Airlines business class in 8 months.”
> “Which of my cards should I use for this ₹40,000 flight booking?”
> “What are my Amex points actually worth, and where should they go?”
> “Which card gets me into the lounge at Delhi T3, and what do I have to activate?”
> “I have 180,000 HDFC points — what is the best thing I can do with them?”

The system should generate:

* optimal card strategies
* reward accumulation plans
* transfer recommendations
* spend routing guidance
* explainable reward simulations

---

# Core Product Philosophy

OptiMILES is NOT:

* a generic chatbot
* **an unopinionated card comparison website** — we compare, but every comparison resolves to a recommendation with the maths shown; a sortable table that leaves the user to decide is the thing we are not
* a broad fintech dashboard
* an AI wrapper
* a banking super app

OptiMILES IS:

* a reward optimization engine
* a financial decision intelligence system
* a travel reward strategy platform
* an explainable optimization system

The platform should feel like:

> “Google Maps for Indian credit card rewards.”

---

# Scope: Breadth With Depth

> **Amended 2026-08-26 — this section replaces "MVP Philosophy" and "Initial MVP Scope".** The MVP is built, demoed and user-tested. It is over. Decision log: `2026-08-26-scope-broadening-and-partner-choice.md`.

## What changed

The MVP was deliberately narrow: **one airline, one goal shape, eight cards**. That narrowness did its job — it forced trustworthy calculations before breadth — and it is now the binding constraint on the product's value. A user whose goal is not Singapore Airlines business class was, structurally, not our user. That has to stop being true.

**The goal is now the Indian rewards ecosystem, not one route through it:** broad card coverage, every meaningful transfer ecosystem, and enough surface area that a rewards question a user actually has is a question we can answer.

## The competitive frame

PointsFly (launched 2026-08-16) is the reference competitor. They went broad first. We went deep first. **Breadth is the gap we are closing; depth is the thing we must not lose while closing it** — anyone can list cards, and the list is not defensible. What is defensible is that every number we show can be traced to a source and its maths displayed.

So the target is: **as comprehensive as the competition, and the only one whose numbers you can check.**

## The tension this creates — read this before adding data

Breadth and line-by-line seed review do not scale together. "Every Indian credit card" and "every row human-verified against a published source" are in direct conflict, and pretending otherwise is how a rewards product ends up confidently wrong.

**The resolution is tiered coverage, stated to the user, never a silent quality gradient:**

* **Verified tier** — full review bar, `source` + `verified_on`, safe for the engine to optimize over and to state as fact. All optimization output must be built from this tier.
* **Listed tier** — broader catalog coverage seeded from published sources but not yet line-by-line verified, carrying `needs_verification: true`. Usable for *informational* surfaces (browse, compare, "what does this card earn"), and the UI must say it is unverified.
* **Not covered** — say so plainly. "We don't cover that card yet" is an acceptable answer; a guess is not.

A card moves tiers by being verified, not by being needed. **No optimization recommendation may be built from unverified rows** — that is the line that keeps breadth from eating the moat.

## Priorities, in order

1. **Trustworthy calculations** — unchanged, and now more load-bearing, not less
2. **Explainable outputs** — every number shows its working
3. **Coverage** — cards, currencies, transfer partners, redemption sweet spots, lounge conditions
4. **Informational depth** — answer the question even when there is no goal yet
5. **Deterministic reward logic** — unchanged
6. **UX clarity** — comprehensive must not become cluttered

Still avoid: feature explosion, excessive automation, unnecessary infrastructure complexity.

---

# Focus Areas

* travel reward optimization
* **all major transfer ecosystems reachable from Indian cards** — KrisFlyer is no longer privileged, and **the product must never assume a target program the user has not chosen** (see *Never Assume the User's Goal* below)
* reward valuation — what points are worth and where they are best spent
* reward accumulation simulations
* spend routing optimization
* transfer partner intelligence
* lounge and benefit intelligence
* explainable recommendations

---

# Never Assume the User's Goal

> Added 2026-08-26 after a real defect: Best Card and Portfolio View priced every wallet in **KrisFlyer miles by default** and printed the program name in the UI, on pages where the user had never stated a goal. The scope document's example goal had leaked into user-facing copy.

Points across issuers are genuinely incommensurable — HDFC Reward Points, EDGE Miles and Membership Rewards are different units, and the catalog carries no ₹-per-point valuation to convert them. Ranking therefore requires a common unit, and a transfer program is the only honest one available.

**That is a reason to ask, not a licence to assume.** The rule:

* Surfaces default to **what the catalog states directly** — points earned, earn rates, caps, benefits
* A **target program is chosen by the user**, or inherited from a goal they actually set
* Where no target is chosen, the product says the cards are not comparable and offers the choice — it does not pick one silently
* A program name appears in the UI only when the user put it there

The engine parameter (`target_program_id`) already existed; the failure was a UI that never surfaced it and a default that spoke with unearned confidence.

---

# Card Coverage

**Depth-verified core** (the MVP nine — full review bar, engine-eligible):

* HDFC Infinia · HDFC Diners Club Black · HDFC Regalia Gold
* HSBC TravelOne
* Axis Atlas · Axis Magnus for Burgundy
* Amex Platinum Travel · Amex Platinum Charge
* SBI Cashback *(deliberate cashback contrast case — must yield zero transfer opportunities)*

**Expansion is now a goal, not an exclusion.** Priority order for new cards: issuers whose currencies unlock transfer ecosystems we do not yet cover, then high-volume premium travel cards, then the broad mid-market. Every addition follows the tiered-coverage rule above.

---

# Exclusions

> **Amended twice on 2026-08-26.** First by `docs/prd/product-roadmap-v1.md` (mobile, Q&A, spend tracking). Then again by the scope broadening above (`2026-08-26-scope-broadening-and-partner-choice.md`), which converts the two coverage exclusions into *goals*. What remains excluded is what we still refuse to build — not what we have not got to yet.

Still excluded:

* browser extensions
* autonomous agents
* financial aggregation systems (bank / Account Aggregator integrations)
* investment features
* geofenced store alerts *(added 2026-08-26 — rejected after competitive triage)*
* **unverified data inside optimization output** — breadth never earns the right to guess (see *Scope: Breadth With Depth*)

No longer excluded — these are now the direction of travel:

* ~~full airline ecosystem support~~ → **a goal.** Every transfer ecosystem reachable from an Indian card, added by coverage priority. KrisFlyer holds no special status.
* ~~every Indian credit card~~ → **broad coverage is a goal**, governed by the tiered-coverage rule rather than by a card count. The exclusion was never really about card *count* — it was about not shipping numbers we could not defend, and that constraint now lives where it belongs.

Overridden earlier the same day — now in the roadmap:

* ~~mobile apps~~ → **Phase 4**, and only after Phases 1–3 land. Web-first → PWA → iOS via Capacitor → Android via TWA. **iOS first, deliberately** (our ICP skews iPhone despite India being ~95% Android). No React Native/Flutter rewrite.
* ~~generic chatbot experiences~~ → **catalog-grounded Q&A is in scope** (Phase 3). Ungrounded chat is still excluded. Every factual claim must trace to a catalog row or engine output; no number is ever LLM-generated.
* ~~automatic spend tracking / OCR-SMS parsing~~ → replaced by **statement/CSV upload + manual log** (Phase 2). The competitor's SMS-parsing version is still rejected — iOS cannot do it at all.

---

# Engineering Philosophy

## Core Principle

Structured systems first.
AI orchestration second.

The system should rely primarily on:

* deterministic logic
* normalized reward schemas
* explicit calculations
* constrained optimization

LLMs should primarily assist with:

* conversational orchestration only (the goal-clarification loop) — **pipeline orchestration is deterministic code**, per `docs/architecture/system-execution-flow-v1.md` §0.2
* summarization
* explanation
* intent extraction
* recommendation narration

LLMs should NOT:

* directly calculate reward values
* hallucinate transfer ratios
* replace structured reward logic
* act as the source of truth

---

# System Architecture Philosophy

The architecture should prioritize:

* modularity
* maintainability
* explainability
* deterministic behavior
* incremental complexity

Avoid:

* premature microservices
* unnecessary abstractions
* overengineered agent systems
* distributed architecture too early
* excessive framework complexity

---

# Recommended Tech Stack

## Frontend

* Next.js
* Tailwind CSS
* shadcn/ui

---

## Backend

* FastAPI
* Python

---

## Database

* Supabase
* PostgreSQL

---

## AI Layer

* OpenAI / Gemini (provider behind one config setting, used only inside `ai_reasoning/`)
* PydanticAI (the two structured LLM calls: intent extraction, narration)
* LangGraph — **deferred**; adopt only if the clarification loop grows real branching (build plan D-3)

---

## Optimization Layer

* Greedy heuristics first (build plan D-7)
* OR-Tools / NetworkX — only behind `generate_candidates()` when a real failing case demands it, never speculatively

---

## Scraping & Data Collection

* Playwright
* BeautifulSoup

---

# Core Backend Systems

## 1. Reward Knowledge Engine

Responsible for:

* card data
* reward rules
* transfer ratios
* milestones
* reward caps
* exclusions

This is the most important system.

---

## 2. Reward Valuation Engine

Responsible for:

* reward value estimation
* transfer value estimation
* redemption calculations
* reward efficiency scoring

---

## 3. Optimization Engine

Responsible for:

* spend allocation
* card strategy generation
* reward maximization
* milestone optimization

Start heuristic-first.
Avoid premature optimization complexity.

---

## 4. Simulation Engine

Responsible for:

* reward accumulation projection
* timeline simulation
* milestone tracking
* redemption readiness estimation

---

## 5. AI Reasoning Layer

Responsible for:

* user intent extraction
* explainable outputs
* strategy narration
* recommendation summaries

NOT direct reward calculations.

---

# Backend Build Rules (Phase 1)

The backend is built to a locked plan. **Entry point: `docs/architecture/backend-build-plan-v1.md`** — read it before touching `backend/`. Canonical references:

* Pipeline & boundaries: `docs/architecture/system-execution-flow-v1.md` (v1.1) — 11 stages; LLM only at Stage 1 (intent, re-validated) and Stage 10 (narration, number-echo-validated with template fallback); Stages 2–9/11 deterministic and replayable from a versioned catalog snapshot.
* Scope: `docs/prd/mvp-scope-v2.md` (canonical; v1 is superseded). Vocabulary: `docs/architecture/core-domain-model-v1.md`.
* Schema: `docs/architecture/db-schema-v1.md` **plus the v1.1 amendment in the build plan §3** (reward currencies, currency-level transfer links, lineage columns).
* Engine behavior: `reward-knowledge-engine-spec-v1.md`, `optimization-engine-spec-v1.md`, `recommendation-engine-design-v1.md`.

Hard rules while building:

1. **The five engines are the module boundary.** Opportunity enumeration lives in `valuation/opportunities.py`; ranking in `optimization/ranking.py`. No sixth engine, no new top-level module without a decision-log entry.
2. **Implementation order is fixed** (build plan §5): domain types → Knowledge (+ `validate_catalog()` + seeds) → Valuation → Simulation → Optimization → AI Reasoning → pipeline/API. Each engine lands fixture-tested (`tdd` skill, mandatory) before the next begins.
3. **Only `knowledge/` and `repositories/` touch the database; only `ai_reasoning/` touches an LLM.** Valuation/Simulation/Optimization are pure functions over the `PlanningContext` snapshot.
4. **Transfer relationships belong to reward currencies, not cards** (build plan D-1). Cards reference their currency; eligibility = card → currency → transfer links.
5. **Reward rules are config, not code:** catalog changes = seed/DB rows; ranking weights = versioned config file. Every seed row carries `source` + `verified_on`; seed PRs get line-by-line human review.
6. **Persist lineage:** `catalog_snapshot_version` + `engine_version` on every `simulation_results` / `recommendation_outputs` row.
7. **Sync single-request pipeline, no queues/workers/events.** 30-second budget (Scope v2); two-part response (structured first, narration second) is the planned API shape.
8. **Determinism is a test:** same goal + user context + snapshot version ⇒ byte-identical results. Keep that end-to-end test green from Phase 6 onward.

---

# AI Collaboration Model

## ChatGPT

Acts as:

* Product Manager
* Systems Architect
* Documentation Lead
* AI Orchestrator

Responsible for:

* PRDs
* architecture
* sprint planning
* UX flows
* final synthesis
* decision logs

---

## Claude

Acts as:

* Senior Software Engineer
* Backend Architect

Responsible for:

* schema design
* backend architecture
* implementation planning
* engineering reviews
* scalability analysis

---

## Gemini

Acts as:

* Research Analyst
* Reward Ecosystem Researcher

Responsible for:

* reward ecosystem research
* airline transfer analysis
* travel card analysis
* external intelligence gathering

---

# Documentation Rules

## Core Principle

Chats are temporary.
Documentation is permanent.

Important decisions must be documented in:

* Notion
* GitHub `/docs`

---

# Documentation Structure

/docs
/prd
/architecture
/research
/ux
/decisions
/prompts

---

# Prompting Standards

Every important AI task prompt should include:

1. ROLE
2. PROJECT CONTEXT
3. OBJECTIVE
4. REQUIREMENTS
5. CONSTRAINTS
6. OUTPUT REQUIREMENTS
7. SAVE OUTPUT AS
8. NOTION LOCATION
9. NOTION STRUCTURE

---

# Workflow Philosophy

AI outputs should:

1. be reviewed
2. be synthesized
3. be validated
4. be documented

No AI-generated output should become production truth without validation.

---

# Product Design Philosophy

The user experience should prioritize:

* clarity
* trust
* explainability
* goal orientation
* strategic guidance

Avoid:

* cluttered dashboards
* excessive fintech jargon
* generic AI chat experiences
* overwhelming recommendation lists

The product should feel:

* intelligent
* premium
* strategic
* trustworthy

---

# Current Development Phase

Current phase:
**Post-MVP Expansion — Phase 1: Daily Surface**, now under the broadened scope (entered 2026-08-26, scope broadened later the same day). The MVP is **over**: built, demoed, user-tested, and no longer the frame. The backend build plan is complete through Phase 7. **Roadmap: `docs/prd/product-roadmap-v1.md`**; **scope: the *Scope: Breadth With Depth* section above, which supersedes the roadmap where they disagree on coverage.**

**Why the phase changed:** user testing validated the goal engine but said "it should be an app"; a competitor (PointsFly, launched 2026-08-16) shipped a broad daily-use feature surface *including* a goal tracker. Goal orientation alone is not the moat — the deterministic, explainable optimization engine is. The MVP answers a once-per-8-months question and gives users no reason to return during accumulation. Phases 1–3 close that retention hole on web; mobile is Phase 4.

**Why the scope broadened (same day, after the first two Phase-1 features shipped):** the narrow SIA/KrisFlyer frame stopped being a discipline and started being a ceiling. It surfaced as a real defect — Best Card and Portfolio View silently priced every wallet in KrisFlyer miles because the scope document said KrisFlyer was primary. The product must now be **valuable, informative and comprehensive across the Indian rewards ecosystem**, and must answer a user's question even when they have no goal yet.

Current priorities (all web — **app conversion comes later**):

* ~~**Best Card for this Spend**~~ — **SHIPPED 2026-08-26** (`valuation/best_card.py`, `GET /v1/best-card`, public `/best-card` page)
* ~~**Portfolio View**~~ — **SHIPPED 2026-08-26** (`valuation/portfolio.py`, `GET /v1/portfolio`, `/cards` leads with it). Ships with a **shared per-device wallet** (`frontend/src/lib/wallet.ts`) that Best Card and the goal wizard also read. Still deferred inside it: cap **utilisation** and milestone **progress** (need Phase 2 spend data) and the fee **calendar** (needs a card-open date we don't collect) — decision log `2026-08-26-portfolio-view-and-shared-wallet.md`
* **Points-first surfaces, user-chosen transfer partner** *(in progress — the fix for the assumed-KrisFlyer defect)*: Best Card and Portfolio View lead with what the catalog states directly (points, earn rates, caps), then *ask* whether the user wants to look at transferring, then let them choose the partner. See *Never Assume the User's Goal*
* **Catalog breadth** — more cards, more currencies, more transfer partners, more redemption data, under the tiered-coverage rule. This is now a standing priority, not a one-off task
* **Sourced ₹-per-point valuations** — the missing number that blocks any honest "what is this worth / what is my best return" answer. Must be seeded with `source` + `verified_on` like any other catalog row; **must never be invented**
* **Lounge Access Intelligence (card side)** — replaces the `has_lounge_access` boolean with real conditions (program, domestic/international counts, quarterly caps, spend-gating, guest rules, enrollment). Needs a migration + seed pass over all 9 cards. Airport *directory* deferred; link out to the programs' own finders instead
* **Mobile-first pass** on the goal wizard and dashboard (built desktop-first; most users reach them on a phone browser)
* then Phase 2 (spend logging → real progress, milestone/cap alerts), then Phase 3 (catalog-grounded Q&A)
* seed-data correctness (still the highest-review-bar artifact in the repo)
* fixture-tested engines (TDD still mandatory for all calculation logic)
* documentation discipline (tracker + decision log stay current as code lands)

NOT:

* Phase 4 mobile work before Phases 1–3 land — wrapping a surface that isn't yet worth opening daily solves nothing
* a React Native / Flutter rewrite (Capacitor over the existing Next.js app; one codebase)
* live award-availability search (deferred pending evidence, not rejected)
* **feature-parity racing for its own sake** — breadth is now a goal, but a feature still has to make a user's decision better. Note this is *narrower* than the old rule: informational surfaces that answer a question without routing to a goal are now legitimate (that was the SIA-era framing talking)
* **inventing a number to fill a gap** — no ₹-per-point valuation, no transfer ratio, no cap, no lounge condition without a source. This is the one rule breadth may never bend
* scaling infrastructure
* autonomous agents

---

# Skills & Agents — When To Use Them

This repo has dedicated skills (`.claude/skills/`) and subagents (`.claude/agents/`) for recurring work. They are not optional extras — treat the "use when" triggers below as part of the workflow, not suggestions to consider only if convenient. Default to invoking the matching skill/agent before doing the task manually.

## Proactive triggers (act on these without being asked)

* **Before implementing any backend calculation, schema rule, or optimization logic** (Reward Knowledge, Valuation, Optimization, or Simulation Engine) → skill `tdd`.
* **After any change under `backend/`**, or when asked to review reward/optimization/simulation logic → agent `backend-reviewer` (read-only).
* **After any change under `frontend/src`**, or when something looks "off"/"messy" or has scrolling/layout issues → agent `frontend-reviewer` (read-only).
* **When scaffolding a new backend module, engine, or significant abstraction** → skill `codebase-design`.
* **When investigating a reported bug, unexpected calculation result, or test failure** — before jumping to a fix → skill `diagnosing-bugs`.
* **At the start of any new chat/task** → skill `tracker-sync` to load `docs/tracker.md` current state.
* **At the end of any session that touched `backend/`, `frontend/`, or `docs/`** → skill `tracker-sync` to refresh the tracker.
* **Whenever something gets built, changed, or decided** — a new feature, schema, architecture choice, scope change, or any "relevant" discussion outcome — file it before ending the session, even if the user doesn't ask. This is the mechanical enforcement of "Chats are temporary. Documentation is permanent." (see Documentation Rules above) → skill `docs-sync`. Don't wait for "document this" — that phrase is a trigger, not a prerequisite.

## Triggered by user phrasing or task shape

* Rough feature idea / "what if we..." / wants to think before spec'ing (not reviewing existing code) → agent `feature-discussion`.
* "Write this up as a PRD" / "spec this out" on an already-shaped idea → agent `prd-writer` (or skill `to-prd` from a conversation/decision directly).
* "Break this down" / "make a task list" / "turn this into issues" from a PRD or decision doc → skill `to-issues`.
* New domain term, inconsistent terminology across `/docs` or code, or modeling a new reward/card/transfer concept → skill `domain-modeling`.
* "Hand this off to ChatGPT/Gemini" / "summarize this for the team" / switching tools mid-task → skill `handoff`.
* Brand/identity/logo/visual-system asset generation → skill `brandkit`.
* `/code-review`, `/simplify`, `/security-review`, `/review` — use as named when the user invokes them or asks for that kind of review.
* User says "grill me" or wants a plan/design stress-tested before building → skill `grill-me` (runs the `grilling` engine: relentless one-question-at-a-time interview with recommended answers, used until the design tree is resolved). Other skills (`codebase-design`, `feature-discussion`, `domain-modeling`, `improve-codebase-architecture`) should invoke `grilling` directly when they need to walk a decision tree with the user instead of re-implementing their own Q&A loop.
* A git merge/rebase stops with conflicts → skill `resolving-merge-conflicts`. Always resolve; never `--abort` or force-push without asking.
* Asked to review or improve backend architecture (not routine feature work, not Phase 0 scaffolding) → skill `improve-codebase-architecture` — scans `backend/` for shallow-module/leaky-seam friction, produces a visual HTML report, then hands the chosen candidate to `grilling`.

## Notes

* `backend-reviewer` and `frontend-reviewer` are read-only — they report findings, they don't edit code. Apply fixes yourself after reading their report.
* Don't spawn an agent or skill redundantly with manual work already in progress — if a proactive trigger applies, invoke it instead of replicating its checklist by hand.
* This list should stay in sync with `.claude/skills/*/SKILL.md` and `.claude/agents/*.md` — if a skill/agent is added, removed, or its triggers change, update this section too.

---

# Guiding Principle

OptiMILES should become:

> The most trustworthy AI reward strategist for Indian rewards — and comprehensive enough that "trustworthy" is worth having.

*(Amended 2026-08-26. The previous version rejected "the largest card database" outright. That was the right instinct at eight cards and the wrong one now: a product that can be trusted about a card you don't hold isn't much use. Breadth is a goal. What was actually being rejected — breadth **instead of** verifiability — still stands, and now lives in the tiered-coverage rule.)*

NOT:

* a card database with no opinion — coverage that doesn't resolve to a recommendation is a table, not a product
* the broadest finance platform (we are rewards, not banking)
* the most feature-rich app
* the smartest chatbot

Depth, trust, explainability, and optimization quality remain the differentiators. **Coverage is what makes them matter.** If the two ever conflict on a specific row, trust wins and we say we don't cover it yet.
