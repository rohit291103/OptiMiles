import { Target, Wallet, Gauge } from "lucide-react";

import { Stagger, StaggerItem } from "@/components/ui/motion";

const PERSONAS = [
  {
    icon: Target,
    title: "Goal chasers",
    quote: "“I want to fly business class on my next big trip.”",
    description:
      "You know the experience you want. OptiMiles works backward from the goal to the exact credit card spend and transfer path that gets you there.",
  },
  {
    icon: Wallet,
    title: "Existing card holders",
    quote: "“I already carry premium credit cards.”",
    description:
      "Before recommending anything new, OptiMiles squeezes the maximum value out of the credit cards already in your wallet.",
  },
  {
    icon: Gauge,
    title: "Reward optimizers",
    quote: "“I want maximum value from every rupee I swipe.”",
    description:
      "Honest point valuations, cap-aware card routing, and an efficiency score per rupee. No marketing math, no guesswork.",
  },
];

export function BuiltFor() {
  return (
    <Stagger className="grid gap-px overflow-hidden rounded-2xl border border-hairline bg-hairline md:grid-cols-[1.15fr_1fr_1fr]">
      {PERSONAS.map((p, i) => (
        <StaggerItem
          key={p.title}
          className={`relative bg-card/40 p-7 backdrop-blur-sm transition-colors hover:bg-card/70 sm:p-8 ${
            i === 0 ? "md:py-10" : ""
          }`}
        >
          <span className="inline-flex size-11 items-center justify-center rounded-xl bg-gold/15 text-gold ring-1 ring-gold/25">
            <p.icon className="size-5" />
          </span>
          <h3 className="mt-5 font-heading text-xl text-foreground">
            {p.title}
          </h3>
          <p className="mt-3 font-heading text-base italic text-gold">
            {p.quote}
          </p>
          <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
            {p.description}
          </p>
        </StaggerItem>
      ))}
    </Stagger>
  );
}
