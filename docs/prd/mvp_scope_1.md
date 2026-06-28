# OptiMILES MVP Scope v1

**Document Path:** `/docs/prd/mvp-scope-v1.md`
**Version:** v1
**Product:** OptiMILES
**Stage:** MVP Definition
**Goal:** Define a narrow-but-deep first version of OptiMILES focused on high-quality reward optimization for Indian users.

---

# 1. MVP Scope

## MVP Objective

Build an AI-powered travel reward optimization platform that helps Indian users achieve a specific premium travel goal through:

* optimal credit card selection
* reward accumulation planning
* spend routing optimization
* airline transfer recommendations
* explainable reward strategy generation

The MVP should feel like:

> “Google Maps for Indian credit card rewards.”

The platform is NOT:

* a generic card comparison site
* a broad fintech dashboard
* a banking super app
* a generic chatbot

---

# Core MVP Workflow

User enters a goal:

> “I want to fly Singapore Airlines business class to Singapore in 9 months.”

System performs:

1. Goal extraction
2. Reward estimation
3. Transfer partner mapping
4. Card strategy generation
5. Spend optimization
6. Timeline simulation
7. Explainable recommendation generation

---

# MVP Philosophy

## Narrow but Deep

The MVP should optimize for:

* quality over breadth
* trustworthy calculations
* explainable outputs
* constrained domain intelligence
* realistic reward simulations

Avoid:

* supporting too many cards
* supporting all airlines
* broad financial planning
* generalized AI advice
* complex automation infrastructure

---

# 2. Supported User Goals

The MVP should support ONLY travel reward goals.

---

## Supported Goal Categories

All three categories below remain in MVP scope. **Flight Redemption is the
category currently surfaced in the product** (the live Goal Simulator); Hotel
and Lounge/Lifestyle goals are planned-but-not-yet-built — modeled in scope and
schema, not yet exposed in the UI.

### A. Flight Redemption Goals  *(surfaced in product)*

Examples:

* Singapore Airlines Business Class
* Emirates Economy
* Air India Business
* Qatar Economy
* Vistara Premium Economy

Supported routes initially:

* India → Singapore
* India → London
* India → New York

> **Implementation note:** the landing-page simulator currently wires exactly
> these three destinations (Singapore, London, New York) as a static mock. An
> earlier scope draft listed Dubai instead of New York; the built product is the
> source of truth — Dubai is a candidate route, not yet wired.

---

### B. Hotel Stay Goals  *(in scope, not yet surfaced)*

Examples:

* Marriott luxury stay
* Accor hotel redemption
* Taj voucher strategy

---

### C. Lounge + Lifestyle Goals  *(in scope, not yet surfaced)*

Examples:

* maximize airport lounge access
* optimize golf/lifestyle benefits
* maximize domestic travel value

---

# Goals NOT Supported in MVP

* cashback-only optimization
* tax optimization
* business expense accounting
* family pooling optimization
* manufactured spending
* crypto/trading integrations
* international credit card recommendations
* forex optimization
* debt management
* investment recommendations

---

# 3. Supported Credit Cards

## Initial Card Universe: 8 Cards (MVP)

The MVP commits to a tight, hand-validated set of 8 cards — deliberately
narrower than the broad "15–20 card" universe explored in research. This keeps
reward modeling, transfer logic, and manual validation tractable while still
spanning the strongest Indian travel-reward ecosystems. This list is the single
source of truth and matches root `CLAUDE.md` → "Initial Supported Cards."

The cards satisfy:

* strong reward ecosystems
* transfer partner support
* premium travel relevance
* high search demand in India

---

## MVP Card List (8)

* HDFC Infinia
* HDFC Diners Black
* HDFC Regalia Gold
* HSBC TravelOne
* Axis Atlas
* Axis Magnus
* Amex Platinum Travel
* SBI Cashback

> **UI note:** the landing page's "cards you already carry" section shows a
> 5-card illustrative wallet (Infinia, Diners Black, Regalia Gold, HSBC
> TravelOne, Amex Platinum Travel) — a deliberate visual subset of this MVP
> set, not the full scope. Axis Atlas, Axis Magnus, and SBI Cashback remain in
> MVP scope but aren't pictured.

> **Deferred (post-MVP candidates):** Amex MRCC, Amex Gold Charge, Axis Select,
> IDFC First Wealth, Yes Marquee, AU Zenith+, Air India SBI Signature, Vistara
> IDFC, Vistara SBI Prime. These came out of ecosystem research but are out of
> the initial 8-card scope to avoid breadth-too-early. Revisit once the core
> engines are validated against the MVP set.

---

# Why This Scope

This set provides:

* strong transfer ecosystems
* realistic optimization opportunities
* enough combinational depth
* manageable reward modeling complexity
* a small enough surface to hand-validate every reward rule

---

# 4. Supported Airlines & Transfer Partners

## Airlines

### Primary Focus

* Singapore Airlines KrisFlyer
* Air India Flying Returns
* Emirates Skywards
* Qatar Airways Privilege Club
* Vistara CV Points (if still relevant operationally)

---

## Hotel Programs

* Marriott Bonvoy
* Accor Live Limitless

---

## Transfer Ecosystems Supported

### Bank Reward Programs

* HDFC Reward Points
* Axis Edge Rewards
* Amex Membership Rewards
* SBI Reward Points
* ICICI Rewards

---

# Transfer Logic Included

The engine should support:

* transfer ratios
* transfer delays
* minimum transfer amounts
* estimated redemption value
* partner eligibility mapping

---

# 5. Included Features

## A. Goal-Based AI Planner

User inputs:

> “I want to fly business class to Singapore in 8 months.”

System extracts:

* destination
* travel class
* timeline
* estimated miles needed

---

## B. Reward Requirement Estimation

System estimates:

* required miles
* taxes/surcharges
* transfer path
* realistic redemption ranges

---

## C. Card Recommendation Engine

Outputs:

* recommended cards
* reasoning
* expected reward velocity
* annual fee justification
* milestone benefits

---

## D. Spend Routing Optimization

Example:

* dining → Card A
* travel → Card B
* utilities → Card C

Optimization objective:
maximize travel reward accumulation.

---

## E. Reward Accumulation Simulator

Inputs:

* monthly spend
* spend categories
* timeline
* current cards

Outputs:

* projected points
* milestone achievement
* estimated redemption readiness

---

## F. Explainable AI Recommendation Layer

The system should explain:

* WHY cards were selected
* WHY transfers matter
* WHY spend routing changes
* WHY one strategy beats another

This is a core differentiator.

---

## G. Structured Reward Knowledge Engine

Internal normalized schema for:

* cards
* reward rates
* caps
* milestones
* transfer ratios
* airline programs

This is foundational infrastructure.

---

## H. Basic Reward News/Update System

Manual or semi-automated updates for:

* devaluations
* transfer ratio changes
* card feature changes

No fully automated scraping infrastructure initially.

---

# 6. Explicitly Excluded Features

## Excluded to Avoid Scope Explosion

### Financial Aggregation

* bank account sync
* statement parsing
* expense tracking

---

### Automation

* automatic spend routing from transactions
* auto card switching
* autopay integrations

---

### Advanced AI Features

* autonomous agents
* multi-step agent orchestration
* memory-heavy personalization
* conversational copilots

---

### Social Features

* community
* referral marketplace
* social feeds

---

### Enterprise Features

* team accounts
* admin dashboards
* analytics suites

---

### Advanced Reward Features

* award seat live inventory
* dynamic flight search engine
* real-time fare tracking
* forex arbitrage
* manufactured spending strategies

---

### Broad Consumer Features

* insurance comparison
* loan recommendations
* mutual funds
* stock investing

---

# 7. Success Criteria

## Product Success Metrics

### User Value Metrics

* users understand recommendations
* users trust calculations
* users can realistically execute strategy

---

## Engagement Metrics

Target:

* users complete a full optimization flow
* users simulate multiple scenarios
* users revisit to adjust goals

---

## Quality Metrics

* accurate reward calculations
* correct transfer logic
* no major recommendation hallucinations
* explainable outputs

---

## MVP Success Definition

The MVP succeeds if:

> A user can input a travel goal and receive a trustworthy, actionable, explainable reward strategy within 30–60 seconds.

---

# 8. Biggest Technical Risks

## A. Reward Data Complexity

Challenge:

* inconsistent card rules
* reward caps
* milestone conditions
* changing transfer ratios

Risk:
incorrect recommendations destroy trust.

Mitigation:

* normalized schemas
* manual validation
* narrow card universe initially

---

## B. Optimization Complexity

Challenge:

* combinational explosion in spend allocation
* milestone interactions
* transfer optimization

Mitigation:

* heuristic-first optimization
* avoid premature OR-Tools complexity initially

---

## C. Hallucinated AI Recommendations

Challenge:
LLMs may fabricate:

* transfer ratios
* eligibility
* reward values

Mitigation:

* structured retrieval layer
* rule-based calculations
* LLM only for explanation/orchestration

---

## D. Data Freshness

Challenge:
reward systems change frequently.

Mitigation:

* manually curated data initially
* lightweight update workflows
* versioned reward configs

---

# 9. Biggest Product Risks

## A. Trust Deficit

Users will not trust:

* black-box recommendations
* inaccurate calculations
* vague AI outputs

Mitigation:

* transparent reasoning
* visible calculations
* explainable strategy generation

---

## B. User Overwhelm

Too many cards/strategies create paralysis.

Mitigation:

* constrained recommendations
* simple outputs
* prioritized action plans

---

## C. Recommendation Quality

Weak recommendations destroy perceived intelligence.

Mitigation:

* optimize depth
* limit supported ecosystems
* heavily validate initial strategies

---

## D. Scope Creep

High risk of:

* becoming a generic finance app
* becoming a card comparison site
* chasing breadth too early

Mitigation:
strict product boundaries.

---

# 10. Recommended MVP Architecture Boundaries

## Guiding Principle

Build only what directly improves:

* recommendation quality
* optimization quality
* simulation accuracy
* explainability

---

# Recommended Architecture

## Frontend

### Stack

* Next.js
* Tailwind
* shadcn/ui

### Responsibilities

* user input flows
* simulation UI
* strategy visualization
* explainability UI

---

## Backend

### Stack

* FastAPI
* Python

### Responsibilities

* reward calculations
* optimization engine
* simulation logic
* transfer calculations
* AI orchestration

---

## Database

### Stack

* PostgreSQL/Supabase

### Store

* cards
* transfer partners
* reward rules
* redemption estimates
* simulations

---

# Core Backend Modules

## A. Reward Knowledge Engine

Structured schemas for:

* cards
* rewards
* categories
* transfer partners
* milestones

This is the most important system.

---

## B. Valuation Engine

Calculates:

* effective reward rates
* transfer values
* redemption estimates

---

## C. Optimization Engine

Inputs:

* spend profile
* goals
* timeline

Outputs:

* optimal card mix
* spend allocation

Start heuristic-based.

---

## D. Simulation Engine

Projects:

* point accumulation
* milestone achievement
* redemption readiness

---

## E. AI Reasoning Layer

Use LLMs ONLY for:

* summarization
* explanation
* strategy narration
* intent extraction

Avoid:

* direct calculation logic
* raw recommendation generation

---

# Architecture Boundaries (Important)

## DO NOT Build Initially

* microservices
* event-driven architecture
* Kubernetes
* graph databases
* vector-heavy systems
* complex agent frameworks
* distributed workflows

---

# Suggested MVP Data Model

## Core Entities

### CreditCard

* issuer
* annual fee
* reward categories
* reward caps
* transfer partners

### TransferPartner

* airline/hotel
* transfer ratio
* transfer time

### RewardRule

* category
* multiplier
* cap
* exclusions

### UserGoal

* destination
* cabin class
* timeline
* points target

### Simulation

* spend assumptions
* projected rewards
* optimization outputs

---

# Final Recommendation

The MVP should focus on becoming:

> The most trustworthy AI reward strategist for Indian travel rewards.

NOT:

* the biggest card database
* the smartest chatbot
* the most feature-rich finance app

Depth, trust, explainability, and optimization quality are the differentiators.
