"use client";

import * as React from "react";

import { cn } from "@/lib/utils";

type RevealProps = React.HTMLAttributes<HTMLDivElement> & {
  /** Render as a different element while keeping reveal behavior. */
  as?: React.ElementType;
  /** Delay in ms before this element animates in (for staggered groups). */
  delay?: number;
  /** Reveal only once, then stop observing. Defaults to true. */
  once?: boolean;
};

/**
 * Dependency-free scroll-reveal. Adds `data-revealed="true"` when the element
 * scrolls into view; the `.reveal` utility in globals.css handles the fade +
 * upward motion and respects prefers-reduced-motion.
 */
export function Reveal({
  as: Tag = "div",
  delay = 0,
  once = true,
  className,
  style,
  children,
  ...props
}: RevealProps) {
  const ref = React.useRef<HTMLDivElement>(null);
  const [revealed, setRevealed] = React.useState(false);

  React.useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setRevealed(true);
            if (once) observer.disconnect();
          } else if (!once) {
            setRevealed(false);
          }
        }
      },
      { threshold: 0.15, rootMargin: "0px 0px -10% 0px" }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [once]);

  return (
    <Tag
      ref={ref}
      data-revealed={revealed}
      className={cn("reveal", className)}
      style={{ "--reveal-delay": `${delay}ms`, ...style } as React.CSSProperties}
      {...props}
    >
      {children}
    </Tag>
  );
}
