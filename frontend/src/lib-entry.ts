/**
 * Library entry for /design-sync.
 *
 * OptiMiles is a Next.js app, not a published component library, so it has no
 * dist/ for the design-sync converter to bundle. This barrel re-exports the
 * components currently covered by Storybook stories so esbuild can compile them
 * into a single `window.OptiMiles` global (the bundle the claude.ai/design agent
 * renders with). Keep this in sync with the *.stories.tsx scope.
 *
 * Imports are RELATIVE (not the "@/" alias) on purpose: the emitted .d.ts is
 * read by the design-sync converter with ts-morph, which doesn't resolve the
 * tsconfig path alias — relative re-exports keep the export surface resolvable.
 *
 * NOT a runtime entry for the app itself — the app imports components by their
 * own paths. This file exists only for the design-system export surface.
 */

// Primitives
export { Button, buttonVariants } from "./components/ui/button";
export { Badge, badgeVariants } from "./components/ui/badge";
export {
  Card,
  CardHeader,
  CardFooter,
  CardTitle,
  CardAction,
  CardDescription,
  CardContent,
} from "./components/ui/card";
export { Input } from "./components/ui/input";

// Section components (self-contained, prop-less)
export { HeroFlow } from "./components/sections/hero-flow";
export { TrustPillars } from "./components/sections/trust-pillars";

// Design-sync preview wrapper (applies the dark-only theme). Referenced by
// cfg.provider; not an app runtime component.
export { DsThemeProvider } from "./components/ds-theme-provider";
