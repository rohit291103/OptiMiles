# Decision Log — Design System Synced to claude.ai/design

**Date:** 2026-06-27
**Area:** Frontend / Tooling
**Branch:** `main`

---

## Context

Following the [Storybook setup](2026-06-27-storybook-setup-for-design-sync.md), the user ran `/design-sync` to import the OptiMiles design system into **claude.ai/design**, so the Claude Design agent builds UIs from our real, compiled components (every design it produces is on-brand and maps to shippable code).

The blocker: OptiMiles is a **Next.js app, not a published component library** — no `dist/`, no package exports, no component barrel. The design-sync converter bundles a library's compiled `dist/` into a `window.<Global>`; there was nothing to bundle. The user chose to **build a library entry** rather than stop.

## Decision

Create a thin library export surface over the existing components and sync the 6 Storybook-covered components (Button, Badge, Card, Input, HeroFlow, TrustPillars) to a new Claude Design project, **OptiMiles Design System** (`8aa116b0-5eef-4309-8ea7-9f68a64c59e6`).

## Implementation

The full reproducible setup lives in `.design-sync/NOTES.md`; the key decisions:

- **Library entry** `frontend/src/lib-entry.ts` — a barrel re-exporting the storied components + a `DsThemeProvider`. esbuild bundles it (react external) into `window.OptiMiles`. No `next/*` imports in the closure, so it bundles cleanly (`motion/react`, `radix-ui`, `lucide-react` all inline).
- **Two non-obvious converter requirements** (both cost a build cycle to discover, both now in NOTES.md):
  1. Re-exports must be **relative**, not the `@/` path alias — the converter's ts-morph export scan doesn't resolve the alias, yielding 0 components.
  2. A real **`.d.ts`** must be emitted (the export surface + prop types are read from it) — added `frontend/tsconfig.dts.json` → `frontend/dist/types`, with a `types` field in `frontend/package.json`.
- **Dark-only theme** via `cfg.provider` → `DsThemeProvider` (wraps previews in `.dark`). The Storybook `.dark` decorator can't be bundled (it imports `globals.css` → `@import "tailwindcss"`, unresolvable by esbuild), so the first build rendered the unstyled LIGHT theme; the provider fixes it.
- **Fonts:** Fraunces (brand heading face) shipped as a real woff2 (Google Fonts, OFL, variable, latin subset) via `cfg.extraFonts`; mono families accepted as system substitutes (user OK'd, suppressed via `runtimeFontPrefixes`).
- **Conventions header** (`.design-sync/conventions.md`, wired via `readmeHeader`) authored for the design agent: dark-only wrapping rule, the semantic Tailwind token vocabulary, and the key gotcha that the **gold CTA is a `className`, not a Button variant**. Every name validated against the built artifacts.

## Verification

- Build + validate clean (no `[FONT_MISSING]`); render-check 6/6 clean (`bad:0, thin:0`).
- compare.mjs captured all 6 components against the reference Storybook; **every story graded `match`** from the side-by-side images (dark/gold theme + Fraunces confirmed rendering correctly). Button's 3 tail stories beyond the 6-story cap are verified-by-upload.
- Closing driver receipt (`resync.mjs`, no `--remote`): `ok: true`, `pendingGrade: []`, all 6 carried forward — the proof the next sync is fast.
- Uploaded via the incremental path (sentinel-fenced; `_ds_sync.json` anchor written last). `report_validate` reported.

## Notes / follow-ups

- **Scope is the 6 storied components.** Adding more = write a story, add to `lib-entry.ts` (relative import), re-emit `.d.ts`, rebuild reference, re-sync. Re-sync risks are enumerated in `.design-sync/NOTES.md`.
- Committed durable state: `.design-sync/{config.json,NOTES.md,conventions.md,fonts/}`, `frontend/src/lib-entry.ts`, `frontend/src/components/ds-theme-provider.tsx`, `frontend/tsconfig.dts.json`, the `types` field. Transient (`sb-reference/`, `.cache/`, `ds-bundle/`, `.ds-sync/`) is gitignored.
