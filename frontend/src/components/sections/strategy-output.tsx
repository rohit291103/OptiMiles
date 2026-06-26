import { CreditCard, ArrowRight, Check } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Reveal } from "@/components/ui/reveal";
import { CountUp } from "@/components/ui/count-up";

const ALLOCATION = [
  { category: "Travel", card: "Axis Atlas" },
  { category: "Dining", card: "HDFC Infinia" },
  { category: "Online", card: "HDFC Infinia" },
  { category: "Everything else", card: "Axis Atlas" },
];

export function StrategyOutput() {
  return (
    <Reveal className="overflow-hidden rounded-[2rem] border border-white/10 bg-card/40 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] backdrop-blur-sm">
      <div className="grid lg:grid-cols-[1.1fr_1fr]">
        {/* Left: the brief */}
        <div className="border-b border-hairline p-8 lg:border-b-0 lg:border-r lg:p-10">
          <p className="text-xs uppercase tracking-[0.2em] text-gold">
            Your strategy
          </p>
          <h3 className="mt-3 font-heading text-2xl text-foreground">
            Long-haul business class
          </h3>

          <dl className="mt-6 space-y-4 text-sm">
            <div className="flex items-center justify-between gap-4">
              <dt className="text-muted-foreground">Current cards</dt>
              <dd className="text-right font-medium text-foreground">
                HDFC Infinia · Axis Atlas
              </dd>
            </div>
            <div className="flex items-center justify-between gap-4">
              <dt className="text-muted-foreground">Monthly spend</dt>
              <dd className="font-medium text-foreground">₹1,00,000</dd>
            </div>
            <div className="flex items-center justify-between gap-4">
              <dt className="text-muted-foreground">Transfer path</dt>
              <dd className="font-medium text-foreground">
                Frequent-flyer transfer (1:1)
              </dd>
            </div>
          </dl>

          <div className="mt-7">
            <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground/70">
              Spend allocation
            </p>
            <ul className="mt-3 space-y-2">
              {ALLOCATION.map((a) => (
                <li
                  key={a.category}
                  className="flex items-center justify-between rounded-lg border border-hairline bg-background/40 px-3 py-2 text-sm"
                >
                  <span className="text-muted-foreground">{a.category}</span>
                  <span className="flex items-center gap-1.5 font-medium text-foreground">
                    <ArrowRight className="size-3.5 text-gold" />
                    <CreditCard className="size-3.5 text-gold" />
                    {a.card}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Right: the projected result */}
        <div className="relative p-8 lg:p-10">
          <div className="pointer-events-none absolute inset-0 bg-aurora" />
          <div className="relative">
            <div className="flex items-center justify-between">
              <p className="text-xs uppercase tracking-[0.2em] text-gold">
                Projection
              </p>
              <Badge className="bg-gold text-gold-foreground hover:bg-gold/90">
                Achievable
              </Badge>
            </div>

            <p className="mt-6 font-heading text-5xl text-foreground">
              <CountUp value={92000} />
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              projected miles
            </p>

            <div className="mt-8 grid grid-cols-2 gap-4">
              <div className="rounded-xl border border-hairline bg-background/40 p-4">
                <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
                  Timeline
                </p>
                <p className="mt-1.5 font-heading text-xl text-foreground">
                  11 months
                </p>
              </div>
              <div className="rounded-xl border border-hairline bg-background/40 p-4">
                <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
                  Confidence
                </p>
                <p className="mt-1.5 font-heading text-xl text-gold">High</p>
              </div>
            </div>

            <ul className="mt-8 space-y-2.5 text-sm text-foreground/90">
              {[
                "Caps and exclusions respected per card",
                "Milestone bonuses factored into the timeline",
                "Every routing decision is explained",
              ].map((line) => (
                <li key={line} className="flex items-start gap-2.5">
                  <span className="mt-0.5 grid size-5 shrink-0 place-items-center rounded-full bg-gold/15 text-gold">
                    <Check className="size-3" />
                  </span>
                  {line}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </Reveal>
  );
}
