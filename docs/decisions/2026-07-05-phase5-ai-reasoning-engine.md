# Decision Log — Phase 5 AI Reasoning Engine (intent extraction + narration)

**Date:** 2026-07-05
**Area:** backend (AI Reasoning Engine — build-plan Phase 5)

## Context

Build-plan Phase 5 is the ONLY LLM-touching engine (build rule 3), covering pipeline Stage 1 (intent extraction & clarification) and Stage 10 (explanation & narration). The user asked to build it now despite not having API keys yet ("i dont have api keys i wil put them later") — which the design accommodates by construction: the whole engine runs correctly with the LLM disabled (structured-form clarification for intent, deterministic templates for narration), and every LLM call is exercised against a fake in tests. Named stack per CLAUDE.md: PydanticAI (structured calls), OpenAI/Gemini behind one config setting.

## Decisions

1. **The LLM sits behind a one-method `ChatModel` protocol** (`ai_reasoning/model.py`): `async complete(instructions, prompt, output_type) -> BaseModel`. Both stages depend only on the protocol; production supplies a PydanticAI adapter, tests supply a `FakeChatModel`, and `model_from_settings()` returns `None` when no key is set. This is what makes "runs without keys" a structural guarantee, not a special case — and it keeps build rule 3 a **one-import truth**: the sole `pydantic_ai` import lives in `_pydanticai.py`, constructed lazily so importing the module never reaches the network.

2. **`pydantic-ai-slim[openai,google]` added as a real dependency now** (user chose "add it now" over deferring). The adapter (`_pydanticai.py`) builds a provider model from settings (`llm_provider` + `llm_model`, new config field with per-provider defaults `gpt-4o-mini`/`gemini-2.0-flash`) and runs a fresh `Agent` per call with the requested `output_type`. It is **deliberately not unit-tested** — mocking PydanticAI's internals would test the mock; its correctness is a live-key smoke test once keys exist. All OptiMiles logic is tested against the fake.

3. **Stage 1 = LLM proposes, deterministic code disposes.** `extract_intent` sends the free-form text plus the catalog VOCABULARY (supported destination cities, cabins, airline program names — **names only, never ratios/miles/earn rates**) and gets a `ParsedGoalIntent` proposal. Then `_revalidate` re-checks every field against the same `CITY_TO_REGION`/`CabinClass` tables Stage 2 uses: an out-of-vocabulary value the model was confident about (`Tokyo`, `"sleeper pod"`) becomes a `missing_field` → `ClarificationRequest`, never a downstream fact. The LLM's confidence buys nothing; only vocabulary membership does. This makes the LLM output safely discardable — the trust boundary is still Stage 2.

4. **Origin city is the only permitted default** (from the user profile, flagged `assumed_fields` so narration can say "assumed you fly from Pune"); every other absent field becomes a clarification question. Out-of-MVP-scope requests ("optimize my taxes") are detected as low-confidence + no usable field (`confidence < 0.25`) and returned as a `ScopeRefusal` — the pipeline never starts.

5. **Stage 10 = the AI sandwich.** `narrate` builds a deterministic `NarrationPayload` of finished numbers and names (headline miles, months-to-goal, fees, card/program names, differentiator, assumptions, adjustment notes — **no score weights, no catalog ids, no ratios**), the LLM only phrases them, then a deterministic **number-echo validator** verifies every integer and every catalog card name in the prose traces to the payload's allow-lists. An unmatched token ⇒ ONE regeneration ⇒ then the template. Card names are guarded against the FULL catalog (a real card cited but not in this plan = hallucination); unknown prose is just prose.

6. **Template fallback ships in the same change and ships the real numbers.** `model=None` (no key) or any LLM exception or a twice-failed echo-check produces a deterministic `RecommendationNarration` assembled from the same payload, `model_version="template-fallback"`. Stilted but true — the numbers ship regardless of LLM availability; only eloquence degrades. The infeasible path (no recommended strategy) narrates the computed adjustment menu, same echo-checking.

7. **`ai_reasoning → knowledge` is a sanctioned cross-engine read** (Stage 1 "Dependencies": "Knowledge Engine read-only vocabulary lists"). The module-boundary AST test now allows it at package level, AND a new dedicated test (`test_ai_reasoning_reaches_only_the_knowledge_vocabulary`) narrows it to `knowledge.goal_resolution` specifically — `knowledge.store` (the DB reader) or any other submodule imported into ai_reasoning fails CI, so the vocabulary read can never widen into DB/catalog access.

## Review outcome (backend-reviewer)

Reviewer confirmed the safety-critical properties: LLM never calculates rewards (re-validation + number-echo both airtight against the tested hallucinations), graceful degradation (model=None and exceptions both fall back, never a 500), module confinement (sole `pydantic_ai` import), determinism, schema consistency with `recommendation_outputs`. Found and I fixed **three findings**, test-first:

- **Critical — decimal-glued bypass.** The number regex `\d[\d,]*` split `97280.7` into `97280`+`7`, both incidentally allow-listed, letting a fabricated decimal pass the one guard the design rests on. Fixed: regex now captures the decimal as one token (`\d[\d,]*(?:\.\d+)?`) and any non-zero fractional part on an always-integer number is rejected outright. Regression test `test_decimal_glued_number_is_rejected`.
- **Important — `raise_spend` false-positive.** The `₹X` amount inside an adjustment-note description is shown to the LLM but wasn't in `allowed_numbers`, so a FAITHFUL echo got wrongly bounced to template. Fixed: every integer in text handed to the LLM (adjustment descriptions + strategy assumptions) is now harvested into `allowed_numbers` via `_integers_in`. Regression test `test_faithful_echo_of_adjustment_amount_is_accepted`.
- **Polish — boundary granularity.** Added the narrowed `knowledge.goal_resolution`-only boundary test (decision 7).

**185/185 total green, mypy strict, ruff clean.**

## Not done (deferred)

- **Live LLM smoke test** — `_pydanticai.py` is untested until keys exist; run one real call per provider when the user adds a key to `backend/.env` (`llm_api_key`, optional `llm_model`).
- **Clarification-loop accumulation** — `extract_intent` handles a single turn; the multi-turn "clarification answers re-enter Stage 1 with accumulated context" loop (blueprint Stage 1) is a pipeline/API concern (Phase 6), not the engine's.
- **DP-07 preference collection** feeding ranking weights still waits on the Goal Discovery UX (carried from Phase 4).
- **Phase 6 (Pipeline + API)** is next: `pipeline/run.py` composing Stages 1–11, persistence with lineage, API v1, the end-to-end determinism test, two-part response (structured first, narration second).
