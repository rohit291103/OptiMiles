import { Target, Wallet, Gauge } from "lucide-react";

import { Reveal } from "@/components/ui/reveal";

const PERSONAS = [
  {
    icon: Target,
    title: "Goal chasers",
    quote: "“I want to fly business class on my next big trip.”",
    description:
      "You know the experience you want. OptiMiles works backward from the goal to the exact spend and transfer path that gets you there.",
  },
  {
    icon: Wallet,
    title: "Existing card holders",
    quote: "“I already carry premium cards.”",
    description:
      "Before recommending anything new, OptiMiles squeezes the maximum value out of the cards already in your wallet.",
  },
  {
    icon: Gauge,
    title: "Reward optimizers",
    quote: "“I want maximum value from every rupee.”",
    description:
      "Honest point valuations, cap-aware routing, and an efficiency score per rupee — no marketing math, no guesswork.",
  },
];

export function BuiltFor() {
  return (
    <div className="grid gap-6 md:grid-cols-3">
      {PERSONAS.map((p, i) => (
        <Reveal
          key={p.title}
          delay={i * 100}
          className="rounded-2xl border border-hairline bg-card/40 p-7 backdrop-blur-sm transition-colors hover:border-gold/40"
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
        </Reveal>
      ))}
    </div>
  );
}
