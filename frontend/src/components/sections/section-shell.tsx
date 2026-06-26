import { cn } from "@/lib/utils";

/**
 * Spatial primitives for the landing page.
 *
 * The page is *edge-to-edge*: there is no centered content box. `Bleed` owns the
 * full viewport width (background, dividers, glow); `Inner` keeps only a small
 * safe gutter so content uses essentially the whole screen — the Apple "the page
 * is the canvas" feel, not a column floating in blank margins. `Measure` opts a
 * single text block back into a readable line-length without re-centering the
 * whole section.
 */

export function Bleed({
  children,
  className,
  id,
  banded,
}: {
  children: React.ReactNode;
  className?: string;
  id?: string;
  /** Tinted, hairline-bordered band — the alternating-section rhythm. */
  banded?: boolean;
}) {
  return (
    <section
      id={id}
      className={cn(
        "relative w-full",
        id && "scroll-mt-24",
        banded && "border-y border-hairline bg-card/20",
        className,
      )}
    >
      {children}
    </section>
  );
}

/**
 * Edge-to-edge content gutter. The only horizontal padding on the page — small,
 * fluid, and the same everywhere so nothing reads as a centered box.
 */
export function Inner({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "w-full px-5 sm:px-8 lg:px-12 xl:px-16 2xl:px-24",
        className,
      )}
    >
      {children}
    </div>
  );
}

/** Constrains a single text block to a comfortable measure, left-aligned by default. */
export function Measure({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <div className={cn("max-w-prose", className)}>{children}</div>;
}
