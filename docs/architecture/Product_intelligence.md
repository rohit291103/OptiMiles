# Product Intelligence Architecture

### The Business Brain of OptiMiles

**Version:** v1.0
**Status:** Canonical Business Architecture
**Audience:** Engineers, AI Coding Agents, Product Managers

---

# Purpose

This document explains **how OptiMiles thinks**.

It defines the business intelligence architecture that powers recommendations before any technical implementation.

Every backend service, API, AI agent and optimization algorithm should follow the principles defined in this document.

This document is intentionally implementation-agnostic and serves as the bridge between product design and engineering.

---

# Product Philosophy

OptiMiles is **not** a credit card comparison website.

It is a goal-based reward optimization platform.

The objective is not to recommend the "best card."

The objective is to help users achieve a specific travel or lifestyle goal using the most effective reward strategy.

Every recommendation must be:

* Goal-driven
* Data-backed
* Explainable
* Deterministic
* Trustworthy

---

# Core Product Principles

### Goal First

Everything begins with the user's goal.

Example:

> Fly Business Class from Mumbai to Singapore.

The system works backwards from the goal instead of forwards from available cards.

---

### Existing Portfolio First

Always maximize value from cards the user already owns.

Only recommend new cards when they provide meaningful improvement.

---

### Deterministic Before AI

Business decisions must come from structured knowledge and deterministic logic.

AI assists with:

* Intent understanding
* Missing information collection
* Recommendation narration

AI never invents reward rules or calculations.

---

### Explainability

Every recommendation must answer:

* Why this strategy?
* Why these cards?
* Why this transfer path?
* Why this timeline?

---

### Unknown Over Incorrect

If required business knowledge is unavailable, the platform must acknowledge uncertainty rather than guess.

---

# Business Intelligence Pipeline

```text
User Goal
        │
        ▼
Goal Understanding
        │
        ▼
Requirement Estimation
        │
        ▼
Reward Knowledge
        │
        ▼
Reward Opportunity Discovery
        │
        ▼
Strategy Generation
        │
        ▼
Strategy Ranking
        │
        ▼
Simulation
        │
        ▼
Recommendation Generation
```

Each stage has a single responsibility.

---

# Core Business Objects

| Object             | Purpose                                          |
| ------------------ | ------------------------------------------------ |
| Goal               | Desired travel or lifestyle outcome              |
| Requirement        | Rewards needed to achieve the goal               |
| Reward Rule        | Atomic reward earning rule                       |
| Reward Opportunity | Possible method of earning rewards               |
| Strategy           | Complete execution plan                          |
| Simulation         | Forecast of strategy execution                   |
| Recommendation     | User-facing explanation of the selected strategy |

---

# Business Engine Responsibilities

## Reward Knowledge Engine

**Owns**

* Credit cards
* Reward rules
* Transfer relationships
* Promotions
* Merchants
* Loyalty programs

**Never**

* Recommend cards
* Rank strategies
* Simulate outcomes

---

## Reward Opportunity Engine

**Owns**

* Discovery of all possible reward earning methods
* Opportunity normalization
* Opportunity classification

**Never**

* Calculate rewards
* Recommend opportunities
* Rank strategies

---

## Strategy Generation Engine

**Owns**

* Candidate strategy generation
* Spend allocation
* Transfer planning
* Card utilization

**Never**

* Rank strategies
* Simulate outcomes

---

## Strategy Ranking Engine

**Owns**

* Multi-objective evaluation
* Trade-off resolution
* Strategy selection

**Never**

* Generate strategies
* Modify strategies

---

## Simulation Engine

**Owns**

* Timeline projection
* Reward accumulation
* Milestone forecasting
* Goal completion forecast

**Never**

* Recommend cards
* Change strategies

---

## Recommendation Engine

**Owns**

* Executive summary
* Overall strategy
* Explanation
* User presentation

**Never**

* Calculate rewards
* Generate business rules

---

# Engine Relationships

```text
Reward Knowledge
        │
        ▼
Reward Opportunity
        │
        ▼
Strategy Generation
        │
        ▼
Strategy Ranking
        │
        ▼
Simulation
        │
        ▼
Recommendation
```

Information flows forward.

Business rules never flow backwards.

---

# AI Boundaries

AI is intentionally limited.

### AI Responsibilities

* Intent extraction
* Goal understanding
* Missing information collection
* Recommendation narration

### Deterministic Responsibilities

* Reward calculations
* Opportunity discovery
* Strategy generation
* Strategy ranking
* Timeline simulation
* Reward math

---

# Business Decision Hierarchy

```text
Business Knowledge

↓

Business Rules

↓

Reward Opportunities

↓

Strategies

↓

Simulation

↓

Recommendation
```

Every decision depends on validated business knowledge.

---

# Recommendation Structure

Every recommendation consists of three layers.

## Executive Summary

* Goal
* Estimated timeline
* Recommended cards
* Expected rewards

---

## Overall Strategy

High-level execution plan.

Example:

**Phase 1**

* Maximize existing cards
* Complete milestones

**Phase 2**

* Apply new card (if justified)
* Optimize spend routing

**Phase 3**

* Transfer rewards
* Redeem
* Complete goal

---

## Detailed Breakdown

* Monthly reward accumulation
* Transfers
* Milestones
* Reward balances
* Progress tracking

---

# Engineering Principles

When implementing any engine:

* One engine owns one responsibility.
* Never duplicate business rules.
* Never bypass the Reward Knowledge Engine.
* Never use AI for deterministic calculations.
* Every calculation must be reproducible.
* Every recommendation must be explainable.
* Unknown data must never be fabricated.

---

# Mapping to Backend

| Business Engine            | Backend Responsibility              |
| -------------------------- | ----------------------------------- |
| Reward Knowledge Engine    | Catalog & business knowledge        |
| Reward Opportunity Engine  | Opportunity discovery               |
| Strategy Generation Engine | Candidate strategy generation       |
| Strategy Ranking Engine    | Multi-objective evaluation          |
| Simulation Engine          | Timeline projection                 |
| Recommendation Engine      | User-facing recommendation assembly |

---

# Engineering Goal

The purpose of the OptiMiles backend is not to return recommendations.

Its purpose is to execute a deterministic business reasoning pipeline that transforms a user's travel goal into an explainable, optimized and trustworthy execution strategy.

Every future implementation decision should preserve this architecture.

---

# End of Document
