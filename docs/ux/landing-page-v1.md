# UX — Landing Page v1 (Design System Baseline)

**Status:** Current implementation (`frontend/src/app/page.tsx`)

---

## Design System

| Element | Choice |
|---|---|
| Theme | Dark-only (`color-scheme: dark`), no light mode toggle in MVP |
| Accent | Gold (`--gold`, oklch(0.74 0.1 75)) — used sparingly for emphasis, CTAs, "Active" status |
| Headings | Fraunces (serif, `font-heading`), italic used for emphasis words |
| Body | Geist Sans |
| Borders | "Hairline" — low-opacity foreground color, not a hard border color |
| Background texture | Subtle dot-grain radial gradient (`.bg-grain`) |

This should feel "intelligent, premium, strategic, trustworthy" per CLAUDE.md's Product Design Philosophy — not a generic SaaS dashboard.

## Page Structure (v1)

1. **Header** — sticky, blurred, logo + anchor nav (Engine / Cards / Simulate) + CTA.
2. **Hero** — single goal statement ("Turn everyday spend into business class, deliberately"), no feature list.
3. **Goal Simulator** (`#simulate`) — the one interactive element; lets a visitor try the core loop before signing up.
4. **Supported cards** (`#cards`) — full roadmap roster grouped by tier, with **Active** (gold) vs **Coming soon** (muted) badges so the MVP scope is honest, not oversold.
5. **Engine philosophy** (`#engine`) — explains the three backend engines (Reward Knowledge, Optimization, Simulation) to reinforce "structured systems first, AI second."
6. **Footer** — minimal, brand + scope line.

## Known constraints

- The Goal Simulator is currently a static mock (`goal-simulator.tsx`) — destinations and mile counts are hardcoded, not wired to a real optimizer. This is correct for the current "frontend shell, no backend yet" phase, but should not be confused with the real Simulation Engine once the backend exists.
- Only 3 destinations (Singapore, London, New York) are wired in the simulator, matching the routes listed in `docs/prd/mvp_scope_1.md`.

## Open questions for future UX work

- What happens when a "Coming soon" card is clicked — nothing yet, intentionally inert in MVP.
- Auth/onboarding flow ("Get started" button) is not yet implemented.
