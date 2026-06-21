"use client";

import * as React from "react";

type CountUpProps = {
  /** Target value to count to. */
  value: number;
  /** Duration of the count animation in ms. Defaults to 1100. */
  duration?: number;
  /** Locale for number formatting. Defaults to en-IN. */
  locale?: string;
  /** Prefix rendered before the number, e.g. "~" or "₹". */
  prefix?: string;
  /** Suffix rendered after the number, e.g. "%". */
  suffix?: string;
  className?: string;
};

const easeOut = (t: number) => 1 - Math.pow(1 - t, 3);

/**
 * Animates a number from 0 to `value` once it scrolls into view. Re-runs
 * whenever `value` changes (e.g. after a simulator recalculation). Honors
 * prefers-reduced-motion by jumping straight to the final value.
 */
export function CountUp({
  value,
  duration = 1100,
  locale = "en-IN",
  prefix = "",
  suffix = "",
  className,
}: CountUpProps) {
  const ref = React.useRef<HTMLSpanElement>(null);
  const [display, setDisplay] = React.useState(0);
  const [inView, setInView] = React.useState(false);

  React.useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true);
          observer.disconnect();
        }
      },
      { threshold: 0.4 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  React.useEffect(() => {
    if (!inView) return;

    const reduced = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;

    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      // With reduced motion, jump straight to the final value on the first frame.
      const progress = reduced ? 1 : Math.min((now - start) / duration, 1);
      setDisplay(Math.round(value * easeOut(progress)));
      if (progress < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [inView, value, duration]);

  return (
    <span ref={ref} className={className}>
      {prefix}
      {display.toLocaleString(locale)}
      {suffix}
    </span>
  );
}
