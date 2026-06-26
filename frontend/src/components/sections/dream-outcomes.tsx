import Image from "next/image";
import { Plane, BedDouble, Sparkles, Armchair } from "lucide-react";

import { Stagger, StaggerItem } from "@/components/ui/motion";

type Outcome = {
  icon: React.ElementType;
  title: string;
  caption: string;
  reward: string;
  timeline: string;
  /** Path under /public, e.g. "/outcomes/business-class.jpg". Outcomes without a
   * photo fall back to the gradient + starfield treatment. */
  image?: string;
  /** Tailwind gradient classes: the fallback / scrim base when no photo is set. */
  gradient: string;
};

const OUTCOMES: Outcome[] = [
  {
    icon: Plane,
    title: "Long-haul business class",
    caption: "Lie-flat to Asia or the Gulf",
    reward: "~92,000 miles",
    timeline: "≈ 11 months",
    image: "/outcomes/business-class.jpeg",
    gradient: "from-amber-500/25 via-card to-background",
  },
  {
    icon: BedDouble,
    title: "Luxury hotel stay",
    caption: "A landmark suite, on points",
    reward: "~120,000 points",
    timeline: "≈ 9 months",
    image: "/outcomes/hotel-suite.jpeg",
    gradient: "from-rose-500/20 via-card to-background",
  },
  {
    icon: Sparkles,
    title: "Premium resort escape",
    caption: "Five nights, fully covered",
    reward: "~85,000 points",
    timeline: "≈ 8 months",
    image: "/outcomes/resort.jpeg",
    gradient: "from-sky-500/20 via-card to-background",
  },
  {
    icon: Armchair,
    title: "Airport lounge access",
    caption: "Skip the terminal, every trip",
    reward: "Milestone perk",
    timeline: "≈ 4 months",
    image: "/outcomes/lounge.jpeg",
    gradient: "from-emerald-500/20 via-card to-background",
  },
];

export function DreamOutcomes() {
  return (
    <Stagger className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
      {OUTCOMES.map((o) => (
        <StaggerItem
          as="article"
          key={o.title}
          whileHover={{ y: -6 }}
          transition={{ type: "spring", stiffness: 300, damping: 24 }}
          className="group relative overflow-hidden rounded-2xl border border-hairline bg-card/40 transition-colors hover:border-gold/40"
        >
          <div
            className={`relative h-40 bg-linear-to-br ${o.gradient}`}
            aria-hidden
          >
            {o.image ? (
              <>
                <Image
                  src={o.image}
                  alt=""
                  fill
                  sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 25vw"
                  className="object-cover transition-transform duration-700 ease-out group-hover:scale-105"
                />
                {/* Darken toward the bottom so the card edge blends into the body
                    and the floating icon stays legible over any photo. */}
                <div className="absolute inset-0 bg-linear-to-t from-card via-card/30 to-background/20" />
              </>
            ) : (
              <div className="absolute inset-0 bg-starfield opacity-40" />
            )}
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
        </StaggerItem>
      ))}
    </Stagger>
  );
}
