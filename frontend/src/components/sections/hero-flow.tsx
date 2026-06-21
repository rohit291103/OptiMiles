"use client";

import { Plane, CreditCard, ArrowLeftRight, Star } from "lucide-react";

import { Reveal } from "@/components/ui/reveal";
import { CountUp } from "@/components/ui/count-up";

type Node = {
  icon: typeof Plane;
  label: string;
  detail: string;
};

const NODES: Node[] = [
  { icon: Plane, label: "Your goal", detail: "Long-haul business class" },
  { icon: CreditCard, label: "Your cards", detail: "HDFC Infinia · Axis Atlas" },
  { icon: ArrowLeftRight, label: "Transfer path", detail: "Frequent-flyer · 1:1" },
  { icon: Star, label: "Redemption", detail: "Ready in 11 months" },
];

/**
 * Hero-side visual: the goal → cards → transfer → redemption journey, with a
 * gold connector that draws itself in. Dependency-free — staggered Reveal for
 * the nodes, a CSS line-draw for the connector, both honoring reduced-motion.
 */
export function HeroFlow() {
  return (
    <div className="relative">
      {/* Soft gold glow behind the flow card */}
      <div className="pointer-events-none absolute -inset-6 bg-aurora opacity-80" />

      <Reveal
        delay={320}
        className="relative rounded-3xl border border-hairline bg-card/40 p-7 backdrop-blur-md sm:p-8"
      >
        <div className="flex items-center justify-between">
          <p className="text-xs uppercase tracking-[0.2em] text-gold">
            Your path
          </p>
          <span className="rounded-full border border-hairline bg-background/50 px-2.5 py-1 text-[11px] text-muted-foreground">
            Explainable
          </span>
        </div>

        <ol className="relative mt-6">
          {/* The drawing connector — sits behind the node icons */}
          <span
            aria-hidden
            className="hero-flow-line absolute left-[1.375rem] top-6 w-px bg-gradient-to-b from-gold/70 via-gold/40 to-gold/10"
          />

          {NODES.map((node, i) => {
            const Icon = node.icon;
            const isLast = i === NODES.length - 1;
            return (
              <Reveal
                as="li"
                key={node.label}
                delay={460 + i * 140}
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
              </Reveal>
            );
          })}
        </ol>

        {/* Projected payoff */}
        <Reveal
          delay={460 + NODES.length * 140}
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
        </Reveal>
      </Reveal>
    </div>
  );
}
