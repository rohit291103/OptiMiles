---
description: Module-design checklist for new OptiMILES backend code — five-engine boundary, no premature abstractions/microservices.
mode: agent
---

Full workflow (canonical): `.claude/skills/codebase-design/SKILL.md` — read it and follow it.

New backend logic slots into one of the five engines defined in root `CLAUDE.md` (Reward Knowledge / Valuation / Optimization / Simulation / AI Reasoning Layer), not a new module invented ad hoc. Before adding a class/interface/service boundary: does it hide real complexity, is there a second concrete caller today, could it just be a plain function instead? No new microservices/queues/agent-frameworks for things deterministic code already handles.
