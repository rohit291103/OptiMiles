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

Example user goal:

> “I want to fly Singapore Airlines business class in 8 months.”

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
* a card comparison website
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

# MVP Philosophy

## Build Narrow and Deep

The MVP should prioritize:

* trustworthy calculations
* explainable outputs
* constrained optimization
* deterministic reward logic
* strong UX clarity

Avoid:

* broad ecosystem support
* feature explosion
* excessive automation
* unnecessary infrastructure complexity

---

# Initial MVP Scope

## Primary MVP Goal

Singapore Airlines business-class optimization using Indian credit cards.

---

## Initial Focus Areas

* travel reward optimization
* KrisFlyer transfer ecosystem
* reward accumulation simulations
* spend routing optimization
* transfer partner intelligence
* explainable recommendations

---

## Initial Supported Cards

* HDFC Infinia
* HDFC Diners Black
* HDFC Regalia Gold
* HSBC TravelOne
* Axis Atlas
* Axis Magnus
* Amex Platinum Travel
* SBI Cashback

---

# Explicit MVP Exclusions

DO NOT build initially:

* browser extensions
* automatic spend tracking
* OCR/SMS parsing
* autonomous agents
* full airline ecosystem support
* every Indian credit card
* mobile apps
* financial aggregation systems
* investment features
* generic chatbot experiences

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

* orchestration
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

* OpenAI / Gemini
* LangGraph
* PydanticAI

---

## Optimization Layer

* OR-Tools
* NetworkX

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
Phase 0 — Product Definition & Architecture

Current priorities:

* MVP scope refinement
* reward ecosystem modeling
* architecture clarity
* UX flow definition
* documentation discipline

NOT:

* scaling infrastructure
* advanced agents
* production optimization
* broad feature expansion

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

> The most trustworthy AI reward strategist for Indian travel rewards.

NOT:

* the largest card database
* the broadest finance platform
* the most feature-rich app
* the smartest chatbot

Depth, trust, explainability, and optimization quality are the core differentiators.
