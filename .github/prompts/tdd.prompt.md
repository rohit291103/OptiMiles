---
description: Red-green-refactor test-first workflow, mandatory for OptiMILES's reward calculation engines.
mode: agent
---

Full workflow (canonical): `.claude/skills/tdd/SKILL.md` — read it and follow it.

Test-first is mandatory for the Reward Knowledge, Valuation, Optimization, and Simulation Engines; lighter touch for the AI Reasoning Layer and frontend. Use concrete golden-value test cases traceable to a real source, plus boundary tests for milestones/caps. Never mock the reward calculation itself to make a test pass.
