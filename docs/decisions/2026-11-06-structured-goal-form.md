# Decision Log: Structured goal form in place of the fill-in-the-blank sentence

**Date:** 2026-11-06
**Area:** Frontend (goal wizard, step 1) and Reward Knowledge (route coverage), plus one new read endpoint
**Supersedes:** the "goal as a sentence" design of slice 10 in `2026-07-13-guided-strategy-flow-design.md`, for step 1 only

## Context

The user found goal entry rigid. Step 1 was one sentence with inline dropdowns: "I want to fly [business] class to [Singapore] from [Hyderabad] within [8] months, for [1 passenger]." It had three problems:

- **The choices were hard-coded.** The frontend had a fixed list of 6 origins and 3 destinations. The backend already accepted 8 origins (Kolkata and Ahmedabad were missing), and nothing tied the lists to the data.
- **It offered combinations the engine can't price.** Award-chart rows exist for India → Singapore in economy, business and first, and for India → London and India → New York in **business only**. The sentence offered "economy to London", which failed at the final step as an unsupported route.
- **Timeline was a bare number of months**, and travellers capped at 4.

## Options put to the user

1. **Input style.** Free text with editable chips, an open structured form, or both. The user chose **an open structured form**.
2. **Uncovered destinations.** Accept them and say so, allow covered cities only, or expand coverage now. The user chose **covered cities only, but searchable**.
3. **Goal types.** The user chose **flights only for now**.

## Decisions

1. **The form is fed by the catalog, not by constants.** A new `GET /v1/catalog/routes` returns covered origins, covered destinations, and the cabins per region pair that have a SAVER award-chart row. The data comes from `knowledge.goal_resolution.covered_routes`, a pure function over the snapshot plus the city table.
   - New chart rows widen the form with no code change.
   - It is ETag'd on the snapshot version, like `/catalog/cards`.
2. **What the form offers, the engine accepts.** A test enforces this contract: every offered (origin, destination, cabin) resolves in Stage 2. Coverage counts only SAVER rows, because that is all Stage 2 matches.
3. **Uncovered cabins are shown disabled, not hidden.** A note names them ("Economy, Premium economy and First aren't covered to London yet"). The user sees what exists and that we can't price it yet, instead of the option silently vanishing.
   - Changing route moves the cabin to business when it is covered, otherwise to the first covered cabin. This happens in the change handler, not in an effect.
4. **No program name in the payload.** The user hasn't chosen one, so the response carries none (CLAUDE.md, *Never Assume the User's Goal*). A test enforces this.
5. **One display name per city.** `CITIES` holds the listed names. `CITY_ALIASES` holds other accepted spellings (Bengaluru, New Delhi, NYC), which Stage 2 still accepts but the form never lists twice. `CITY_TO_REGION` is derived from both, so the free-text intent path is unchanged.
6. **When = a travel month**, 1–36 months ahead ("Jul 2027 · In 8 months — the time you have to earn the miles"). It still sends `timeline_months`. The engine's target date is today + N months, so the label and the engine agree.
7. **Travellers is a 1–9 stepper.** The engine has no cap; the old list stopped at 4.

## Deliberately not done

- **Return trips.** `RewardRequirement.one_way` is hard-coded and goals are persisted one-way. Return trips need the requirement maths, persistence and taxes per direction (the seeded taxes are India-origin only). That is engine work, so it is TDD-first and a separate slice.
- **Free-text entry.** `/goals/parse` still depends on the rate-limited free LLM tier. The user chose a structured form.
- **Coverage expansion.** More destinations need sourced award charts. That falls under the tiered-coverage rule and stays a standing data priority.

## Verification

- Backend:
  - 6 coverage tests (golden coverage from the seeds, alias de-duplication, data-driven drop-out, SAVER-only, every offered combination resolves)
  - 2 endpoint tests (shape and no program name, ETag 304)
  - Suite 734 → 742. mypy strict and ruff are clean.
- Frontend: tsc and eslint are clean (`next build` not run, because the dev server holds `.next`). Driven headless at 1440×900 and 390×844:
  - choosing London leaves only Business enabled
  - "tokyo" shows "We don't cover 'tokyo' yet" and Escape restores the committed city
  - no horizontal overflow and no console errors
- A live `POST /v1/simulations` for Kolkata → London, business, 2 travellers, 14 months returns a recommendation. This goal was not expressible before.
