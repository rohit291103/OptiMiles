import { Plane, Building2, CreditCard } from "lucide-react";

type Entry = { icon: React.ElementType; label: string };

// Kept generic per the project's brand-cleanup decision: categories of partners,
// not named airlines/hotels we can't yet guarantee in the optimizer.
const ENTRIES: Entry[] = [
  { icon: Plane, label: "Frequent-flyer programs" },
  { icon: Building2, label: "Hotel loyalty programs" },
  { icon: CreditCard, label: "HDFC" },
  { icon: CreditCard, label: "Axis" },
  { icon: CreditCard, label: "American Express" },
  { icon: Plane, label: "Airline transfer partners" },
  { icon: Building2, label: "Hotel transfer partners" },
];

function Track({ ariaHidden = false }: { ariaHidden?: boolean }) {
  return (
    <ul
      className="flex shrink-0 items-center gap-4 px-2"
      aria-hidden={ariaHidden || undefined}
    >
      {ENTRIES.map((e, i) => (
        <li
          key={`${e.label}-${i}`}
          className="flex items-center gap-2.5 whitespace-nowrap rounded-xl border border-hairline bg-card/40 px-5 py-3 text-sm text-muted-foreground"
        >
          <e.icon className="size-4 text-gold" />
          {e.label}
        </li>
      ))}
    </ul>
  );
}

export function EcosystemMarquee() {
  return (
    <div className="group relative overflow-hidden">
      {/* Edge fades */}
      <div className="pointer-events-none absolute inset-y-0 left-0 z-10 w-16 bg-linear-to-r from-background to-transparent" />
      <div className="pointer-events-none absolute inset-y-0 right-0 z-10 w-16 bg-linear-to-l from-background to-transparent" />

      <div className="flex w-max animate-marquee group-hover:[animation-play-state:paused] motion-reduce:animate-none">
        <Track />
        <Track ariaHidden />
      </div>
    </div>
  );
}
