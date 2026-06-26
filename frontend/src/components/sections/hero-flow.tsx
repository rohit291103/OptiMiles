"use client";

import { motion, useReducedMotion } from "motion/react";
import { Plane, CreditCard, ArrowLeftRight, Star } from "lucide-react";

import { CountUp } from "@/components/ui/count-up";

const EASE = [0.16, 1, 0.3, 1] as const;

type Node = {
  icon: typeof Plane;
  label: string;
  detail: string;
};

const NODES: Node[] = [
  { icon: CreditCard, label: "Your cards", detail: "HDFC Infinia · Axis Atlas" },
  { icon: Plane, label: "Your goal", detail: "Long-haul business class" },
  {
    icon: ArrowLeftRight,
    label: "Card-to-card routing",
    detail: "Spend mapped, card by card",
  },
  { icon: Star, label: "Redemption", detail: "Ready in 11 months" },
];

/**
 * Hero-side visual: the cards → goal → routing → redemption journey. The nodes
 * cascade in and a gold connector draws itself down between them. The outer
 * entrance/rotation is owned by <Hero>; this just orchestrates the inner motion.
 */
export function HeroFlow() {
  const reduced = useReducedMotion();

  return (
    <div className="relative">
      {/* Soft gold glow behind the flow card */}
      <div className="pointer-events-none absolute -inset-6 bg-aurora opacity-80" />

      <div className="relative rounded-[2rem] border border-white/10 bg-card/50 p-7 shadow-[inset_0_1px_0_rgba(255,255,255,0.08),0_30px_60px_-30px_rgba(0,0,0,0.6)] backdrop-blur-md sm:p-8">
        <div className="flex items-center justify-between">
          <p className="text-xs uppercase tracking-[0.2em] text-gold">
            Your card strategy
          </p>
          <span className="rounded-full border border-hairline bg-background/50 px-2.5 py-1 text-[11px] text-muted-foreground">
            Explainable
          </span>
        </div>

        <motion.ol
          className="relative mt-6"
          initial={reduced ? undefined : "hidden"}
          animate={reduced ? undefined : "show"}
          variants={{
            hidden: {},
            show: { transition: { staggerChildren: 0.16, delayChildren: 1 } },
          }}
        >
          {/* The drawing connector, sits behind the node icons */}
          <motion.span
            aria-hidden
            className="absolute left-5.5 top-6 bottom-11 w-px origin-top bg-linear-to-b from-gold/70 via-gold/40 to-gold/10"
            initial={reduced ? undefined : { scaleY: 0 }}
            animate={reduced ? undefined : { scaleY: 1 }}
            transition={{ duration: 1.4, ease: EASE, delay: 1.1 }}
          />

          {NODES.map((node, i) => {
            const Icon = node.icon;
            const isLast = i === NODES.length - 1;
            return (
              <motion.li
                key={node.label}
                variants={{
                  hidden: { opacity: 0, x: 12 },
                  show: {
                    opacity: 1,
                    x: 0,
                    transition: { duration: 0.6, ease: EASE },
                  },
                }}
                className={`relative flex items-center gap-4 ${isLast ? "" : "pb-6"}`}
              >
                <span
                  className={`relative z-10 grid size-11 shrink-0 place-items-center rounded-xl border ${
                    isLast
                      ? "border-gold/50 bg-gold/15 text-gold"
                      : "border-hairline bg-background/70 text-foreground"
                  }`}
                >
                  <Icon className="size-5" />
                </span>
                <div className="min-w-0">
                  <p className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
                    {node.label}
                  </p>
                  <p className="truncate text-sm font-medium text-foreground">
                    {node.detail}
                  </p>
                </div>
              </motion.li>
            );
          })}
        </motion.ol>

        {/* Projected payoff */}
        <motion.div
          initial={reduced ? undefined : { opacity: 0, y: 12 }}
          animate={reduced ? undefined : { opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: EASE, delay: 1.9 }}
          className="mt-6 flex items-end justify-between border-t border-hairline pt-5"
        >
          <div>
            <p className="font-heading text-3xl leading-none text-foreground">
              <CountUp value={92000} />
            </p>
            <p className="mt-1 text-xs text-muted-foreground">projected miles</p>
          </div>
          <div className="text-right">
            <p className="font-heading text-base text-gold">High confidence</p>
            <p className="mt-1 text-xs text-muted-foreground">
              caps &amp; milestones factored in
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
