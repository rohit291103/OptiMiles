---
description: Sharpen OptiMILES reward/finance vocabulary and check for inconsistent term usage across docs/code.
mode: agent
---

Full workflow (canonical): `.claude/skills/domain-modeling/SKILL.md` — read it and follow it.

Quick reference: transfer ratio (bank's fixed rate) ≠ valuation (effective value achieved); accrual (earned) ≠ transfer (moved between programs) ≠ redemption (converted to reward); milestone (bonus trigger) ≠ reward cap (payout ceiling). Canonical definition order on conflict: `docs/architecture/db-schema-v1.md` → `docs/prd/mvp_scope_1.md` → root `CLAUDE.md`. Flag conflicts rather than silently rewriting historical docs.
