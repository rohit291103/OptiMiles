"use client";

import {
  Route,
  ShieldCheck,
  LineChart,
  Wallet,
  Check,
} from "lucide-react";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const FEATURES = [
  {
    value: "route",
    tab: "Spend routing",
    icon: Route,
    title: "Route every rupee to the right card",
    description:
      "OptiMiles decides which card to swipe for each spend category — and stops earning on a card the moment its cap is hit, redirecting to the next-best option automatically.",
    points: [
      "Category-aware allocation across all your cards",
      "Cap, milestone and exclusion aware",
      "Clear ‘why this card’ explanation on every call",
    ],
  },
  {
    value: "valuation",
    tab: "Valuation",
    icon: Wallet,
    title: "Know what a point is actually worth",
    description:
      "Reward currencies are normalized to a single, honest value so you can compare a cashback rupee against a transferable mile without the marketing math.",
    points: [
      "Transfer-partner valuation, not face value",
      "Redemption-grade point pricing",
      "Efficiency score per rupee spent",
    ],
  },
  {
    value: "simulate",
    tab: "Simulation",
    icon: LineChart,
    title: "Watch your goal resolve over time",
    description:
      "Set a destination, a cabin, and a date. OptiMiles projects your accumulation timeline and tells you the month you become redemption-ready.",
    points: [
      "Month-by-month accumulation timeline",
      "Milestone and bonus tracking",
      "Redemption-readiness estimate",
    ],
  },
  {
    value: "trust",
    tab: "Explainability",
    icon: ShieldCheck,
    title: "Deterministic logic, not a hallucinating bot",
    description:
      "Every recommendation traces back to a normalized reward schema and explicit calculation. The AI narrates the strategy — it never invents the numbers.",
    points: [
      "Versioned, auditable reward rules",
      "No guessed transfer ratios",
      "Source-of-truth you can verify",
    ],
  },
];

export function FeatureTabs() {
  return (
    <Tabs defaultValue="route" className="gap-8">
      <TabsList className="mx-auto flex-wrap">
        {FEATURES.map((f) => (
          <TabsTrigger key={f.value} value={f.value}>
            <f.icon />
            <span className="hidden sm:inline">{f.tab}</span>
          </TabsTrigger>
        ))}
      </TabsList>

      {FEATURES.map((f) => (
        <TabsContent key={f.value} value={f.value}>
          <div className="grid items-center gap-10 rounded-3xl border border-hairline bg-card/40 p-8 backdrop-blur-sm lg:grid-cols-2 lg:p-12">
            <div>
              <span className="inline-flex size-12 items-center justify-center rounded-xl bg-gold/15 text-gold ring-1 ring-gold/25">
                <f.icon className="size-6" />
              </span>
              <h3 className="mt-6 font-heading text-2xl text-foreground sm:text-3xl">
                {f.title}
              </h3>
              <p className="mt-4 text-base leading-relaxed text-muted-foreground">
                {f.description}
              </p>
              <ul className="mt-6 space-y-3">
                {f.points.map((p) => (
                  <li key={p} className="flex items-start gap-3 text-sm text-foreground/90">
                    <span className="mt-0.5 grid size-5 shrink-0 place-items-center rounded-full bg-gold/15 text-gold">
                      <Check className="size-3" />
                    </span>
                    {p}
                  </li>
                ))}
              </ul>
            </div>

            <div className="relative hidden h-full min-h-72 overflow-hidden rounded-2xl border border-hairline bg-background/40 lg:block">
              <div className="absolute inset-0 bg-aurora" />
              <div className="relative flex h-full flex-col justify-center gap-4 p-8">
                {f.points.map((p, i) => (
                  <div
                    key={p}
                    className="flex items-center gap-3 rounded-xl border border-hairline bg-card/70 px-4 py-3 text-sm text-foreground shadow-sm"
                    style={{ marginLeft: `${i * 1.5}rem` }}
                  >
                    <f.icon className="size-4 text-gold" />
                    {p}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </TabsContent>
      ))}
    </Tabs>
  );
}
