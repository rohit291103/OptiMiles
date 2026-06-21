---
name: tdd
description: Red-green-refactor test-first workflow, mandatory for anything in the Reward Knowledge, Valuation, Optimization, or Simulation Engines; lighter-touch for UI/presentation code. Use proactively before implementing any backend calculation, schema rule, or optimization logic.
---

# tdd

Root `CLAUDE.md` calls deterministic reward logic the MVP's foundation and explicitly forbids LLMs from being "the source of truth" for reward values — which means the structured code that *is* the source of truth has to be verifiably correct. Tests are how "verifiably" stops being a word and becomes a fact.

Check `docs/tracker.md` (via the `tracker-sync` skill) before starting — confirm the engine you're testing is the one actually in scope for this session, not one still marked "Next up."

## Where this is mandatory vs. optional

- **Mandatory, test-first:** any code in the Reward Knowledge Engine (card rules, transfer ratios, milestones, caps, exclusions), Reward Valuation Engine (value/efficiency scoring), Optimization Engine (spend allocation, strategy generation), Simulation Engine (accumulation projection, redemption readiness). These are the "deterministic logic" CLAUDE.md says the system must rely on primarily — they get the strictest discipline.
- **Lighter touch:** AI Reasoning Layer (narration/summarization) and frontend presentation — test the contract (given this input, narration mentions the right numbers) rather than exact wording.

## The loop

1. **Red** — write a failing test that encodes the expected behavior from the spec (PRD, schema doc, or a stated business rule like a published transfer ratio). For reward math, prefer concrete golden-value cases over abstract property checks first ("HDFC Infinia, ₹1L spend, non-forex category → exactly X points") — concrete cases catch the off-by-one and wrong-constant bugs that matter most here.
2. **Green** — write the minimum code to pass. Resist adding handling for cases the test suite doesn't yet demand.
3. **Refactor** — clean up only with the safety net of passing tests; don't refactor and add behavior in the same step.

## Test design notes specific to this domain

- **Golden-value tests** for each supported card's documented reward rates and transfer ratios — these should be traceable to a source (a card's published T&C or `docs/research/`), not invented numbers, so a future rate change is an obvious, intentional test update rather than a silent drift.
- **Boundary tests** for milestones and caps — exactly-at-threshold and one-unit-under/over are where these bugs live.
- **No mocking the reward calculation itself** — if a test mocks out the Valuation Engine to test something else, that's fine, but never mock reward math to make a test pass; that defeats the entire point of this skill existing.

## Scope discipline

Per CLAUDE.md's MVP Philosophy ("avoid... unnecessary infrastructure complexity"), don't introduce a testing framework, fixture system, or CI pipeline beyond what's needed to run the tests that exist today. Match whatever's already configured in `backend/` once it exists; don't pre-build infrastructure for tests that don't exist yet.
