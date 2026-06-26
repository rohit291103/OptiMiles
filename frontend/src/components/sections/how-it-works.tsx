import { Target, Wallet, Sparkles, LineChart } from "lucide-react";

import { Reveal } from "@/components/ui/reveal";

const STEPS = [
  {
    icon: Target,
    step: "Step 1",
    title: "Choose a travel goal",
    description:
      "Pick the trip you actually want: a cabin, a region, a hotel tier, and a date you'd like to take it by.",
  },
  {
    icon: Wallet,
    step: "Step 2",
    title: "Tell us your cards and spending",
    description:
      "Share which credit cards you already carry and roughly what you spend each month. No statements, no SMS, no tracking.",
  },
  {
    icon: Sparkles,
    step: "Step 3",
    title: "Get a card-by-card strategy",
    description:
      "OptiMiles tells you which credit card to use for each spend category and charts the transfer path to your goal, with the reasoning shown.",
  },
  {
    icon: LineChart,
    step: "Step 4",
    title: "Track your progress",
    description:
      "Watch your accumulation timeline resolve month by month and see exactly when your goal becomes achievable.",
  },
];

export function HowItWorks() {
  return (
    <div className="relative">
      {/* Progress connector, horizontal on lg, hidden on small screens. */}
      <div
        className="absolute left-0 right-0 top-7 hidden lg:block"
        aria-hidden
      >
        <div className="mx-auto h-px max-w-[78%] bg-linear-to-r from-transparent via-gold/40 to-transparent" />
      </div>

      <ol className="grid gap-10 lg:grid-cols-4 lg:gap-6">
        {STEPS.map((s, i) => (
          <Reveal
            as="li"
            key={s.step}
            delay={i * 120}
            className={`relative ${i % 2 === 1 ? "lg:mt-12" : ""}`}
          >
            <span
              aria-hidden
              className="pointer-events-none absolute -top-6 right-0 font-heading text-7xl text-foreground/5 sm:text-8xl"
            >
              {String(i + 1).padStart(2, "0")}
            </span>
            <div className="relative flex items-center gap-4 lg:flex-col lg:items-start">
              <span className="relative z-10 inline-flex size-14 shrink-0 items-center justify-center rounded-2xl border border-gold/25 bg-background text-gold shadow-sm">
                <s.icon className="size-6" />
              </span>
              <p className="text-xs uppercase tracking-[0.2em] text-gold lg:mt-6">
                {s.step}
              </p>
            </div>
            <h3 className="relative mt-3 font-heading text-lg text-foreground">
              {s.title}
            </h3>
            <p className="relative mt-2 text-sm leading-relaxed text-muted-foreground">
              {s.description}
            </p>
          </Reveal>
        ))}
      </ol>
    </div>
  );
}
