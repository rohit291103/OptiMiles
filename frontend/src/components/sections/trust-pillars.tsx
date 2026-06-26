import { Database, TrendingUp, LineChart, ShieldCheck } from "lucide-react";

import { FadeUp } from "@/components/ui/motion";

const PILLARS = [
  {
    icon: Database,
    title: "Structured card intelligence",
    description:
      "Every credit card's transfer ratio, reward rule, cap, and milestone is modeled and versioned. Nothing is guessed, nothing is hallucinated.",
  },
  {
    icon: TrendingUp,
    title: "Card routing engine",
    description:
      "Each rupee is routed to the highest-value card for that spend category, against real-world caps, exclusions, and milestones.",
  },
  {
    icon: LineChart,
    title: "Reward simulation",
    description:
      "Project your accumulation against a single goal and see exactly when it becomes achievable month by month.",
  },
  {
    icon: ShieldCheck,
    title: "Explainable recommendations",
    description:
      "Every recommendation comes with its reasoning and tradeoffs. The AI narrates the strategy; it never invents the numbers.",
  },
];

export function TrustPillars() {
  return (
    <div className="grid gap-6 sm:grid-cols-2">
      {PILLARS.map((p, i) => (
        <FadeUp
          key={p.title}
          delay={i * 0.08}
          className="group relative overflow-hidden rounded-2xl border border-hairline bg-card/40 p-7 backdrop-blur-sm transition-all hover:-translate-y-1 hover:border-gold/40"
        >
          <div className="pointer-events-none absolute -right-10 -top-10 size-32 rounded-full bg-gold/10 opacity-0 blur-2xl transition-opacity group-hover:opacity-100" />
          <span className="relative inline-flex size-12 items-center justify-center rounded-xl bg-gold/15 text-gold ring-1 ring-gold/25">
            <p.icon className="size-6" />
          </span>
          <h3 className="relative mt-5 font-heading text-xl text-foreground">
            {p.title}
          </h3>
          <p className="relative mt-3 text-sm leading-relaxed text-muted-foreground">
            {p.description}
          </p>
        </FadeUp>
      ))}
    </div>
  );
}
