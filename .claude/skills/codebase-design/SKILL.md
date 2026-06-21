---
name: codebase-design
description: Vocabulary and checklist for designing deep, maintainable backend modules per CLAUDE.md's System Architecture Philosophy (modularity, incremental complexity, no premature microservices/abstractions). Use proactively when scaffolding a new backend module, engine, or significant abstraction.
---

# codebase-design

Root `CLAUDE.md`'s System Architecture Philosophy is explicit about what to avoid: premature microservices, unnecessary abstractions, overengineered agent systems, distributed architecture too early, excessive framework complexity. This skill is the checklist to run before adding structure, not after — overengineering is far cheaper to prevent than to unwind.

## The five backend systems are the module boundary

CLAUDE.md already defines the module decomposition — don't invent a different one:

1. Reward Knowledge Engine (card data, rules, transfer ratios, milestones, caps, exclusions)
2. Reward Valuation Engine (value/transfer/redemption estimation, efficiency scoring)
3. Optimization Engine (spend allocation, strategy generation — "start heuristic-first, avoid premature optimization complexity")
4. Simulation Engine (accumulation projection, timeline/milestone tracking)
5. AI Reasoning Layer (intent extraction, narration — explicitly NOT calculation)

A new piece of backend logic should slot into one of these five, not spawn a sixth without a clear reason it doesn't fit. If it genuinely doesn't fit, say so explicitly and explain why before creating a new module.

## "Deep module" checklist before adding an abstraction

A deep module (simple interface, does meaningful work behind it) beats a shallow one (interface as complicated as the implementation). Before adding a new class/interface/service boundary, check:

- Does this hide real complexity, or just rename a single function call? (If the latter, skip it.)
- Could this be a plain function in the existing engine's module instead of a new class/service?
- Is there a second concrete caller today, or is this "for later"? CLAUDE.md's MVP Philosophy says avoid building for hypothetical future requirements — one caller doesn't justify an abstraction layer.
- Does it cross a boundary that needs to be a boundary (e.g. Reward Knowledge Engine output feeding Valuation Engine input), or is it splitting something that's naturally one piece?

## Anti-patterns flagged by this skill

- A new microservice/separate deployable for what could be a module in the existing FastAPI app — Phase 0 explicitly excludes "scaling infrastructure" and "advanced agents" (CLAUDE.md, Current Development Phase).
- A generic plugin/strategy-pattern system built before there are ≥2 concrete variants needing it.
- LangGraph/agent orchestration introduced for something deterministic logic already handles — per the Engineering Philosophy, AI orchestration is second, not first.

## When this skill is satisfied

The result should be boring: a small number of clearly-bounded modules matching the five backend systems, plain functions/classes within them, and zero new infrastructure (queues, services, frameworks) that wasn't already in the Recommended Tech Stack.
