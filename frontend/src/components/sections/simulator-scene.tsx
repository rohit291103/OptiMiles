"use client";

import { Sparkles } from "lucide-react";
import { motion, useReducedMotion } from "motion/react";

const EASE = [0.16, 1, 0.3, 1] as const;

/**
 * The simulator section — product-first, directly under the hero.
 *
 * Deliberately NOT a pinned scroll scene: the simulator is interactive (you
 * fill in fields and read expanding results), and pinning hijacks the scroll
 * wheel and clips the results, which felt "stuck." Instead it's a normal,
 * freely-scrollable block with a one-time scale/fade *entrance* as it comes
 * into view — the cinematic feel without trapping the scroll. Edge-to-edge,
 * sticky intro copy on wide screens. Calm + static under reduced-motion.
 */
export function SimulatorScene({ children }: { children: React.ReactNode }) {
  const reduced = useReducedMotion();

  return (
    <section
      id="simulate"
      className="relative scroll-mt-24 overflow-hidden border-y border-hairline bg-card/20 py-24 sm:py-28 lg:py-32"
    >
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-linear-to-r from-transparent via-gold/40 to-transparent" />
      <div className="grid w-full grid-cols-1 items-center gap-14 px-5 sm:px-8 lg:grid-cols-[0.85fr_1.15fr] lg:items-start lg:gap-16 lg:px-12 xl:px-16 2xl:px-24">
        <motion.div
          initial={reduced ? undefined : { opacity: 0, y: 28 }}
          whileInView={reduced ? undefined : { opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.4 }}
          transition={{ duration: 0.8, ease: EASE }}
          className="lg:sticky lg:top-28"
        >
          <Copy />
        </motion.div>

        <motion.div
          initial={reduced ? undefined : { opacity: 0, y: 60, scale: 0.95 }}
          whileInView={reduced ? undefined : { opacity: 1, y: 0, scale: 1 }}
          viewport={{ once: true, amount: 0.25 }}
          transition={{ duration: 0.9, ease: EASE, delay: 0.1 }}
          className="relative"
        >
          <div className="pointer-events-none absolute -inset-10 bg-aurora opacity-70" />
          <div className="relative">{children}</div>
        </motion.div>
      </div>
    </section>
  );
}

function Copy() {
  return (
    <div className="max-w-xl">
      <p className="flex items-center gap-2 text-xs uppercase tracking-[0.22em] text-gold">
        <Sparkles className="size-3.5" /> Try it now
      </p>
      <h2 className="mt-5 font-heading font-light leading-[0.95] tracking-tight text-foreground text-[clamp(2.75rem,6vw,5.5rem)]">
        Pick your cards. <br />
        <span className="italic text-gold">See the path.</span>
      </h2>
      <p className="mt-7 max-w-md text-base leading-relaxed text-muted-foreground sm:text-lg">
        No sign-up, no statements read. Choose a destination, a cabin, and the
        credit cards already in your wallet, then watch the timeline resolve in
        front of you.
      </p>
      <ul className="mt-9 space-y-3 text-sm text-muted-foreground">
        <Point>Cards you already carry, mapped spend-by-spend.</Point>
        <Point>A dated timeline to your seat, not a vague score.</Point>
        <Point>Caps, milestones and transfer ratios accounted for.</Point>
      </ul>
    </div>
  );
}

function Point({ children }: { children: React.ReactNode }) {
  return (
    <li className="flex items-start gap-3">
      <span className="mt-2 size-1.5 shrink-0 rounded-full bg-gold" />
      <span className="leading-relaxed">{children}</span>
    </li>
  );
}
