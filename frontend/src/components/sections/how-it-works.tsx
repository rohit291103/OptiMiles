import { Target, Wallet, Sparkles, LineChart } from "lucide-react";

import { Reveal } from "@/components/ui/reveal";

const STEPS = [
  {
    icon: Target,
    step: "Step 1",
    title: "Choose a travel goal",
    description:
      "Pick the trip you actually want — a cabin, a region, a hotel tier — and a date you'd like to take it by.",
  },
  {
    icon: Wallet,
    step: "Step 2",
    title: "Tell us your spending",
    description:
      "Share roughly what you spend each month and which cards you already carry. No statements, no SMS, no tracking.",
  },
  {
    icon: Sparkles,
    step: "Step 3",
    title: "Get an optimized strategy",
    description:
      "OptiMiles routes each spend category to the right card and charts the transfer path to your goal — with the reasoning shown.",
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
      {/* Progress connector — horizontal on lg, hidden on small screens. */}
      <div
        className="absolute left-0 right-0 top-7 hidden lg:block"
        aria-hidden
      >
        <div className="mx-auto h-px max-w-[78%] bg-linear-to-r from-transparent via-gold/40 to-transparent" />
      </div>

      <ol className="grid gap-8 lg:grid-cols-4">
        {STEPS.map((s, i) => (
          <Reveal as="li" key={s.step} delay={i * 120} className="relative">
            <div className="flex items-center gap-4 lg:flex-col lg:items-start">
              <span className="relative z-10 inline-flex size-14 shrink-0 items-center justify-center rounded-2xl border border-gold/25 bg-background text-gold shadow-sm">
                <s.icon className="size-6" />
              </span>
              <p className="text-xs uppercase tracking-[0.2em] text-gold lg:mt-6">
                {s.step}
              </p>
            </div>
            <h3 className="mt-3 font-heading text-lg text-foreground">
              {s.title}
            </h3>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              {s.description}
            </p>
          </Reveal>
        ))}
      </ol>
    </div>
  );
}
