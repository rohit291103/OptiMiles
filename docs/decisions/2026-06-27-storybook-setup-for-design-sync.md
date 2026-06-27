# Decision Log — Storybook Setup (Vite adapter) for the Frontend Design System

**Date:** 2026-06-27
**Area:** Frontend / Tooling
**Branch:** `main`

---

## Context

The user invoked `/design-sync` to sync the OptiMiles design system to claude.ai/design (so the design agent builds with our real components). The skill needs either a compiled component-library `dist/` or a Storybook to drive a high-fidelity, screenshot-verified import.

OptiMiles has neither: `frontend/` is a private Next.js **app**, not a published component package, and there is no Storybook. The shadcn-style primitives in `src/components/ui/` are app source, not an exported, buildable library.

Given the choice (hold off / force the lower-fidelity package path / add Storybook first), the user chose **add Storybook first** — it unlocks the high-fidelity sync path later and is useful on its own for developing primitives in isolation. The actual design-sync upload was **not** run this session.

## Decision

Stand up Storybook over the existing frontend, scoped to the UI primitives plus a couple of self-contained section components. Defer the claude.ai/design upload to a future session.

## Implementation

- **Storybook 10.4.6** with the **`@storybook/nextjs-vite`** (Vite) adapter — chosen over the webpack adapter for speed and cleaner Tailwind v4 integration. Verified against the live npm registry that 10.4.6 declares peer support for **Next 16 / React 19** (not assumed from training data, per `frontend/AGENTS.md`'s "this is NOT the Next.js you know" warning).
- Added dev deps: `storybook`, `@storybook/nextjs-vite`, `@storybook/addon-docs`, `@storybook/addon-a11y`, `vite@^7`, `@tailwindcss/vite@^4`.
- **`.storybook/main.ts`** — registers `@tailwindcss/vite` (Tailwind v4 the app's `@import "tailwindcss"` entry depends on), mirrors the app's `@/* → ./src/*` path alias in `viteFinal`, serves `../public` as static dir.
- **`.storybook/preview.ts`** — imports the app's real `globals.css`; a decorator forces the **`.dark`** class on `<html>`/`<body>` because the site is dark-only and the gold/`--gold` tokens exist *only* under `.dark` (without this, every preview would silently render the unstyled light theme).
- **`.storybook/preview.css`** — a shim mapping the `--font-geist-sans` / `--font-geist-mono` / `--font-fraunces` variables (normally injected by `next/font` in `layout.tsx`, which the Vite adapter never runs) to close system-font stacks, preserving the serif-display vs. sans contrast.
- **Stories (6 files, 28 stories):** `button`, `badge`, `card`, `input` primitives; `hero-flow`, `trust-pillars` sections (both prop-less and self-contained). Story args/variants were written against each component's *actual* API (read from source), not assumed.
- `package.json` scripts: `storybook`, `build-storybook`. `frontend/.gitignore` ignores `/storybook-static`.

## Verification

- `npm run build-storybook` completed successfully — proves the toolchain compiles on Next 16 / React 19 / Tailwind v4 (Vite adapter, Tailwind v4 plugin, `@/` alias all working). Only warning is a benign large-chunk notice from Storybook's own DocsRenderer/iframe bundles.
- `storybook dev` served HTTP 200 and `index.json` registered all 28 stories.
- **Not yet done:** a human visual pixel-check in the browser that the dark/gold theme and font shim actually render as intended (compile/serve success ≠ correct render — the exact trap `CLAUDE.md` flags for UI work). The `.dark` decorator and font shim are the two render-time risks to eyeball.

## Notes / follow-ups

- **design-sync upload deferred.** With Storybook in place, a future `/design-sync` run can take the high-fidelity, screenshot-verified storybook path. No `.design-sync/` config was created this session.
- If/when more components are synced, expand story coverage beyond the current 6 — the section components beyond HeroFlow/TrustPillars pull in app data/layout and need more decorator setup.
- The font shim uses system fallbacks, not the real Geist/Fraunces faces. If pixel-accurate type matters for the sync, load the actual fonts in `preview.ts` instead.
