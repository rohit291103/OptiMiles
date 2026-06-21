import { Plane, BedDouble, Sparkles, Armchair } from "lucide-react";

import { Reveal } from "@/components/ui/reveal";

type Outcome = {
  icon: React.ElementType;
  title: string;
  caption: string;
  reward: string;
  timeline: string;
  /** Tailwind gradient classes used as a stand-in for destination photography. */
  gradient: string;
};

const OUTCOMES: Outcome[] = [
  {
    icon: Plane,
    title: "Long-haul business class",
    caption: "Lie-flat to Asia or the Gulf",
    reward: "~92,000 miles",
    timeline: "≈ 11 months",
    gradient: "from-amber-500/25 via-card to-background",
  },
  {
    icon: BedDouble,
    title: "Luxury hotel stay",
    caption: "A landmark suite, on points",
    reward: "~120,000 points",
    timeline: "≈ 9 months",
    gradient: "from-rose-500/20 via-card to-background",
  },
  {
    icon: Sparkles,
    title: "Premium resort escape",
    caption: "Five nights, fully covered",
    reward: "~85,000 points",
    timeline: "≈ 8 months",
    gradient: "from-sky-500/20 via-card to-background",
  },
  {
    icon: Armchair,
    title: "Airport lounge access",
    caption: "Skip the terminal, every trip",
    reward: "Milestone perk",
    timeline: "≈ 4 months",
    gradient: "from-emerald-500/20 via-card to-background",
  },
];

export function DreamOutcomes() {
  return (
    <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
      {OUTCOMES.map((o, i) => (
        <Reveal
          as="article"
          key={o.title}
          delay={i * 90}
          className="group relative overflow-hidden rounded-2xl border border-hairline bg-card/40 transition-colors hover:border-gold/40"
        >
          <div
            className={`relative h-40 bg-linear-to-br ${o.gradient}`}
            aria-hidden
          >
            <div className="absolute inset-0 bg-starfield opacity-40" />
            <span className="absolute left-4 top-4 inline-flex size-10 items-center justify-center rounded-xl bg-background/50 text-gold ring-1 ring-gold/25 backdrop-blur-sm">
              <o.icon className="size-5" />
            </span>
          </div>
          <div className="p-5">
            <h3 className="font-heading text-lg text-foreground">{o.title}</h3>
            <p className="mt-1 text-sm text-muted-foreground">{o.caption}</p>
            <dl className="mt-4 flex items-center justify-between border-t border-hairline pt-4 text-xs">
              <div>
                <dt className="uppercase tracking-[0.12em] text-muted-foreground/70">
                  Reward
                </dt>
                <dd className="mt-1 font-heading text-sm text-gold">
                  {o.reward}
                </dd>
              </div>
              <div className="text-right">
                <dt className="uppercase tracking-[0.12em] text-muted-foreground/70">
                  Timeline
                </dt>
                <dd className="mt-1 font-heading text-sm text-foreground">
                  {o.timeline}
                </dd>
              </div>
            </dl>
          </div>
        </Reveal>
      ))}
    </div>
  );
}
