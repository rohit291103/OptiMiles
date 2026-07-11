# Decision Log — Branded loaders + delete-confirmation modal

**Date:** 2026-07-11
**Area:** frontend

## Context

Three UX complaints about the signed-in surface:

1. **Deleting a saved goal felt unprofessional** — the confirm was a cramped two-step inside the three-dot dropdown ("click Delete, and 'Confirm' appears in the same tiny spot"). Easy to misfire; not what a premium product does.
2. **Loading screens "went dark"** — the dashboard and goal-detail routes showed bare pulsing skeleton boxes with no life or brand.
3. **The strategy-generation wait had no animation** — clicking "Build my card strategy" left the screen static with only a disabled button label, for a wait that can run tens of seconds.

## Decisions

1. **New reusable `components/ui/confirm-dialog.tsx` — a real modal, not an inline confirm.** Portal-rendered (escapes the trigger's overflow/stacking context), dimmed `backdrop-blur` overlay, `motion` enter/exit, focus moved to the confirm button on open, a **Tab focus-trap** cycling between the only two focusable elements (Cancel/Confirm), Escape + backdrop-click to dismiss. A `busy` state disables dismissal and both buttons so a delete can't be double-fired or interrupted; on failure the dialog **stays open with the error inline** rather than silently resetting. `destructive` variant for the delete framing. The dialog owns no domain logic — the caller passes open state + both handlers.
2. **`GoalMenu` delete now opens that modal.** The old `confirming-delete` in-menu state and its `MenuState` union were removed; "Delete goal" closes the popover and opens `ConfirmDialog`. Optimistic removal (`onDeleted`) still runs only after the `DELETE /goals/{id}` 204.
3. **New branded `components/ui/plane-loader.tsx`.** A self-contained SVG: a plane flies a dotted great-circle arc via CSS `offset-path`, drawing a gold `motion` trail, with a pulsing destination pin and a status line that cycles through copy mirroring the real 11-stage pipeline ("Pulling verified award charts…", "Routing your spend for maximum miles…", "Writing your strategy…"). `prefers-reduced-motion` renders the arc static with a single steady line. No external assets (CSP-safe), no layout shift (fixed-height status line).
4. **The loader is used in all three wait surfaces.** It leads the dashboard (`(app)/goals/page.tsx`) and goal-detail (`(app)/goals/[id]/page.tsx`) skeletons (with short, page-appropriate two-line copy) above the existing shape-preserving skeleton, and fills the simulator's results area (`goal-simulator.tsx`) while `loading`.
5. **Accessibility cleanup from review.** The skeleton wrappers no longer declare their own `role="status"` (the `PlaneLoader` is the single live region; the skeleton is `aria-hidden`). The scroll-lock effect reads `busy`/`onCancel` via refs so it depends only on `open` (no teardown churn on every busy flip). Dialog panel got `max-h-[85vh] overflow-y-auto` as defensive polish for long content on short viewports.

## Not done (deferred)

- **`offset-path` has no Safari support** (as of Safari 18 / iOS 18). On Safari the plane renders static at the arc's origin — the trail/pins and status copy still animate, so the loader degrades gracefully rather than breaking. Accepted; not worth a JS-driven fallback for the primary Chromium audience. Flagged for any future Safari-testing pass.
- **Backend latency, not a frontend change:** the reviewer measured `/simulations` at 36–44s live, over the 30s Scope-v2 budget. The loader handles it gracefully (holds on the final stage), but the latency itself is a separate backend item.

## Verification

- `tsc --noEmit` + `eslint` clean on all changed files.
- frontend-reviewer real-browser pass (desktop 1440×900 + mobile 390×844): loader renders correctly (plane follows the arc — confirmed via `getComputedStyle(...).offsetPath` + screenshots mid-flight), no horizontal overflow, no console/motion warnings across three full simulate runs, no layout jump when the result replaces the loader. Its findings (missing Tab trap vs. the "focus-trapped" docstring claim, scroll-lock churn, nested `role="status"`, dialog overflow) were all applied.
- The delete modal and the two authed loading skeletons could not be driven live (behind Google OAuth) — verified statically; they reuse the same primitives verified on the public simulator.
