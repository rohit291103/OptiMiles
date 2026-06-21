---
applyTo: "backend/**"
---

Apply `.claude/skills/codebase-design/SKILL.md` and `.claude/skills/tdd/SKILL.md` (read both) to any code in this path.

Non-negotiable: never let an LLM call's output flow directly into a reward/points/value number returned to a user — deterministic calculation must sit in between (root `CLAUDE.md`'s Engineering Philosophy). New logic belongs in one of the five backend engines (Reward Knowledge / Valuation / Optimization / Simulation / AI Reasoning Layer) — don't invent a sixth without explaining why. Calculation code needs golden-value tests traceable to a real source plus boundary tests for milestones/caps. No new microservices, queues, or agent-orchestration frameworks for things a plain function could do.
