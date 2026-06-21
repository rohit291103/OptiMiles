---
name: diagnosing-bugs
description: Disciplined reproduce-minimize-hypothesize-instrument-fix-test debugging loop, with reward/transfer/valuation calculation bugs treated as highest severity. Use proactively whenever investigating a reported bug, an unexpected calculation result, or a test failure — before jumping to a fix.
---

# diagnosing-bugs

Guessing at a fix before understanding the failure wastes more time than it saves, and in OptiMILES a guessed "fix" to reward math is worse than a slow correct one — root `CLAUDE.md` names "trustworthy calculations" as the MVP's first priority. This skill is the loop to run before editing code in response to a bug report.

## Severity triage first

Before debugging mechanics, classify the bug:

- **Critical** — wrong output from the Reward Knowledge, Valuation, Optimization, or Simulation Engines (wrong transfer ratio, wrong points total, wrong milestone trigger, wrong redemption value). These are silent-failure-prone because they still "look" plausible. Stop and fix before doing anything else.
- **Important** — UI/UX bugs that misrepresent correct underlying data (e.g. a correct number rendered in the wrong place).
- **Minor** — cosmetic, no data/logic implication.

## The loop

1. **Reproduce** — get a minimal, deterministic repro before touching code. For calculation bugs: the exact input (card, spend amount, category, dates) and the exact expected vs. actual output. If it's not reproducible, that itself is the finding — don't fix what you can't observe.
2. **Minimize** — strip the repro to the smallest input that still triggers it. For reward math, this usually means isolating one card/one rule/one transfer step rather than a full simulation run.
3. **Hypothesize** — state a specific, falsifiable cause before reading further code ("the milestone threshold check uses `>` instead of `>=`"), not "something's off in the calculation."
4. **Instrument** — add the minimum logging/assertions to confirm or kill the hypothesis. Prefer reading values at engine boundaries (input to Reward Knowledge Engine, output of Valuation Engine) over scattering prints everywhere.
5. **Fix** — the smallest change that addresses the confirmed root cause. Don't bundle unrelated cleanup into a bug-fix commit.
6. **Test** — for any Critical-tier bug, the fix isn't done until there's a regression test pinning the previously-wrong case to the correct value (see the `tdd` skill). A reward-math bug fixed without a test is the same bug waiting to come back.

## Anti-patterns to avoid

- Patching symptoms in the UI/AI narration layer when the root cause is in a deterministic engine — the AI Reasoning Layer must never become a workaround for incorrect upstream math (root `CLAUDE.md`: "LLMs should NOT directly calculate reward values").
- Declaring a fix done because the one reported case now works, without checking adjacent cases (other cards, boundary milestone values, zero-spend edge cases).
