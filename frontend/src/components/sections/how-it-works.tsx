"use client";

import * as React from "react";
import { motion, useReducedMotion, useScroll, useTransform } from "motion/react";
import { Target, Wallet, Sparkles, LineChart } from "lucide-react";

import { FadeUp } from "@/components/ui/motion";

const EASE = [0.16, 1, 0.3, 1] as const;

const STEPS = [
  {
    icon: Target,
    step: "01",
    title: "Choose a travel goal",
    description:
      "Pick the trip you actually want: a cabin, a region, a hotel tier, and a date you'd like to take it by.",
  },
  {
    icon: Wallet,
    step: "02",
    title: "Tell us your cards and spending",
    description:
      "Share which credit cards you already carry and roughly what you spend each month. No statements, no SMS, no tracking.",
  },
  {
    icon: Sparkles,
    step: "03",
    title: "Get a card-by-card strategy",
    description:
      "OptiMiles tells you which credit card to use for each spend category and charts the transfer path to your goal, with the reasoning shown.",
  },
  {
    icon: LineChart,
    step: "04",
    title: "Track your progress",
    description:
      "Watch your accumulation timeline resolve month by month and see exactly when your goal becomes achievable.",
  },
];

/**
 * Sticky scroll-pinned sequence. On large screens the left column pins while
 * the four steps scroll past on the right; the step nearest the viewport
 * centre lights up and a gold progress rail fills as you scroll. Collapses to
 * a simple revealed stack on small screens and under reduced-motion.
 */
export function HowItWorks() {
  const reduced = useReducedMotion();
  const containerRef = React.useRef<HTMLDivElement>(null);
  const [active, setActive] = React.useState(0);

  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start center", "end center"],
  });
  const railScaleY = useTransform(scrollYProgress, [0, 1], [0, 1]);

  return (
    <div ref={containerRef} className="mx-auto max-w-6xl px-6 py-28">
      <div className="grid gap-12 lg:grid-cols-[0.85fr_1.15fr] lg:gap-16">
        {/* Pinned left column */}
        <div className="lg:sticky lg:top-28 lg:h-fit lg:self-start">
          <FadeUp>
            <p className="text-xs uppercase tracking-[0.22em] text-gold">
              How it works
            </p>
            <h2 className="mt-4 font-heading text-3xl tracking-tight text-foreground sm:text-5xl">
              Four steps from credit card spend{" "}
              <span className="italic text-gold">to redemption.</span>
            </h2>
            <p className="mt-5 max-w-sm text-muted-foreground">
              Goal first, then a card-by-card strategy. You stay in control the
              whole way.
            </p>

            {/* Step ticker, reflects the active step on scroll */}
            <div className="mt-10 hidden items-center gap-3 lg:flex">
              {STEPS.map((s, i) => (
                <span
                  key={s.step}
                  className={`h-1 rounded-full transition-all duration-500 ${
                    i === active ? "w-10 bg-gold" : "w-5 bg-hairline"
                  }`}
                />
              ))}
            </div>
          </FadeUp>
        </div>

        {/* Scrolling steps with a gold progress rail */}
        <div className="relative">
          {!reduced && (
            <>
              <div className="absolute left-7 top-0 bottom-0 hidden w-px bg-hairline lg:block" />
              <motion.div
                style={{ scaleY: railScaleY }}
                className="absolute left-7 top-0 bottom-0 hidden w-px origin-top bg-gold lg:block"
              />
            </>
          )}

          <ol className="space-y-10 lg:space-y-16">
            {STEPS.map((s, i) => (
              <Step
                key={s.step}
                {...s}
                index={i}
                onActive={() => setActive(i)}
              />
            ))}
          </ol>
        </div>
      </div>
    </div>
  );
}

function Step({
  icon: Icon,
  step,
  title,
  description,
  index,
  onActive,
}: {
  icon: React.ElementType;
  step: string;
  title: string;
  description: string;
  index: number;
  onActive: () => void;
}) {
  const reduced = useReducedMotion();

  return (
    <motion.li
      className="relative flex gap-6"
      initial={reduced ? undefined : { opacity: 0, y: 30 }}
      whileInView={reduced ? undefined : { opacity: 1, y: 0 }}
      viewport={{ amount: 0.6, margin: "-20% 0px -20% 0px" }}
      onViewportEnter={onActive}
      transition={{ duration: 0.7, ease: EASE, delay: index * 0.05 }}
    >
      <span className="relative z-10 inline-flex size-14 shrink-0 items-center justify-center rounded-2xl border border-gold/25 bg-background text-gold shadow-sm">
        <Icon className="size-6" />
      </span>
      <div className="pt-1">
        <p className="font-heading text-sm text-gold">{step}</p>
        <h3 className="mt-1 font-heading text-xl text-foreground sm:text-2xl">
          {title}
        </h3>
        <p className="mt-3 max-w-md leading-relaxed text-muted-foreground">
          {description}
        </p>
      </div>
    </motion.li>
  );
}
