---
description: Disciplined reproduce-minimize-hypothesize-instrument-fix-test debugging loop for OptiMILES bugs.
mode: agent
---

Full workflow (canonical): `.claude/skills/diagnosing-bugs/SKILL.md` — read it and follow it.

Triage first: wrong output from the Reward Knowledge/Valuation/Optimization/Simulation Engines is Critical — fix before anything else. Loop: reproduce (minimal, deterministic) → minimize → hypothesize (specific, falsifiable) → instrument (smallest logging) → fix (smallest change) → test (Critical bugs need a regression test pinning old-wrong-value to correct). Never patch a calculation bug in the AI narration layer instead of the underlying deterministic logic.
