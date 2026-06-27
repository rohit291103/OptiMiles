# design-sync NOTES — OptiMiles

OptiMiles is a **Next.js app, not a published component library**, so the
storybook-shape sync needed extra scaffolding to produce a bundle. Everything
below is what makes the build reproducible.

## Build setup (general)

- **[GENERAL] No dist/ — a library entry was created.** `frontend/src/lib-entry.ts`
  is a barrel re-exporting the storied components (+ `DsThemeProvider`). The
  converter is pointed at it via `--entry frontend/src/lib-entry.ts`.
  Keep it in sync with the `*.stories.tsx` scope.
- **[GENERAL] Re-exports MUST be relative, not the `@/` alias.** The converter's
  ts-morph export scan does NOT resolve the tsconfig `@/*` path alias, so
  `export { X } from "@/components/..."` yields **0 exports** (`[TITLE_UNMAPPED]`,
  0 components). `lib-entry.ts` uses relative `./components/...` paths for this
  reason.
- **[GENERAL] `.d.ts` must be emitted before the build.** The converter reads the
  public-export surface from `.d.ts` (`pkgJson.types`). The app emits none, so:
  `cd frontend && npx tsc -p tsconfig.dts.json` (emits to `frontend/dist/types`,
  `types` field points at `dist/types/lib-entry.d.ts`). **Re-run this whenever a
  component's props change OR the barrel changes**, before `package-build.mjs`.
- **[GENERAL] Dark-only theme via `cfg.provider`.** The site's gold/dark tokens
  live under the `.dark` class in globals.css. Storybook applies it with a
  decorator, but the converter can't bundle that decorator (it imports
  globals.css → `@import "tailwindcss"`, unresolvable by esbuild →
  `! preview decorator bundle failed`). Fix: `DsThemeProvider`
  (`frontend/src/components/ds-theme-provider.tsx`) wraps every preview in
  `.dark bg-background text-foreground` via `cfg.provider`. Without it, previews
  render the unstyled LIGHT theme (verified: that's exactly what happened on the
  first build).
- **CSS comes from the storybook build** (`[CSS_FROM_STORYBOOK]`) — there's no DS
  css dist, so the converter scrapes the compiled Tailwind v4 css out of
  `.design-sync/sb-reference`. Rebuild the reference if globals.css changes.
- **Fonts:** Fraunces (brand heading face) is shipped via
  `cfg.extraFonts: ["../.design-sync/fonts/fraunces.css"]` — a real woff2 fetched
  from Google Fonts (OFL, variable, latin subset) + an `@font-face` and a
  `--font-fraunces` definition (next/font normally sets that variable; it doesn't
  run in the bundle). Mono families (Cascadia/Roboto Mono/etc.) are accepted as
  **system substitutes** (user OK'd "best judgment") — suppressed via
  `cfg.runtimeFontPrefixes`. They only appear in CSS fallback chains, not in any
  of the 6 components.

## Commands to reproduce (in order)

```bash
# 1. reference storybook (the fidelity oracle)
cd frontend && npx storybook build -c "$(git rev-parse --show-toplevel)/frontend/.storybook" \
  -o "$(git rev-parse --show-toplevel)/.design-sync/sb-reference"
# 2. emit .d.ts (export surface + prop types)
cd frontend && npx tsc -p tsconfig.dts.json
# 3. converter + validate + compare (from repo root)
node .ds-sync/package-build.mjs --config .design-sync/config.json \
  --node-modules frontend/node_modules --entry frontend/src/lib-entry.ts --out ./ds-bundle
node .ds-sync/package-validate.mjs ./ds-bundle
node .ds-sync/storybook/compare.mjs --out ./ds-bundle --storybook-static .design-sync/sb-reference
```

## Re-sync risks (watch these next run)

- **Scope is 6 components only** (button, badge, card, input, hero-flow,
  trust-pillars) — exactly the storied set. Adding a component means: write its
  story, add it to `lib-entry.ts` (relative import), re-emit `.d.ts`, rebuild the
  reference, rebuild.
- **Button has 9 stories, capped at 6 graded** (`[STORY_CAP]`). The tail 3
  (`With Icon`, `All Variants`, `Sizes`) are verified-by-upload, not
  individually graded. Pass `--max-stories 9` if those variants need explicit
  verification.
- **`frontend/dist/types` is gitignored** (it's under `frontend/.gitignore`? — it
  is NOT; `dist/types` is emitted into `frontend/dist`). If `frontend/dist` is
  ever cleaned, step 2 must re-run before any rebuild or exports drop to 0.
- **`frontend/package.json` carries a `types` field** added for this sync
  (`dist/types/lib-entry.d.ts`). It's harmless to the app (private, no consumers)
  but is design-sync scaffolding, not app config.
- **Fraunces is a latin-subset variable font.** Non-latin glyphs fall back. The
  woff2 is committed under `.design-sync/fonts/`.
- **Substituted mono fonts** are a deliberate, user-approved fidelity compromise.
