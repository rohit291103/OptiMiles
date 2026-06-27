import * as React from "react";

/**
 * Design-sync preview wrapper. The OptiMiles site is dark-only: the gold/dark
 * design tokens in globals.css live under the `.dark` class, and `html` sets
 * `color-scheme: dark`. Storybook applies this via a `.dark` decorator, but the
 * design-sync converter can't bundle that decorator (it imports globals.css ->
 * `@import "tailwindcss"`, which esbuild can't resolve), so previews would
 * render the unstyled LIGHT theme.
 *
 * This component is referenced by `cfg.provider` so every generated preview
 * mounts inside `.dark bg-background text-foreground`, exactly like the app.
 * It is part of the library export surface only for that purpose.
 */
export function DsThemeProvider({ children }: { children?: React.ReactNode }) {
  return (
    <div className="dark bg-background text-foreground" style={{ colorScheme: "dark" }}>
      {children}
    </div>
  );
}
