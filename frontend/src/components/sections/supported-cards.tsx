import Image from "next/image";

import { Badge } from "@/components/ui/badge";

type Card = {
  name: string;
  tier: string;
  active: boolean;
  /** Path under /public, e.g. "/cards/infinia.png". */
  image: string;
};

// An illustrative example wallet, not the full supported set. Breadth lives in
// the "Supported ecosystems" section; this is just "the cards you already carry."
const CARDS: Card[] = [
  {
    name: "HDFC Infinia",
    tier: "Premium Travel",
    active: true,
    image: "/cards/infinia.png",
  },
  {
    name: "HDFC Diners Club Black",
    tier: "Premium Travel",
    active: true,
    image: "/cards/diners-black.png",
  },
  {
    name: "HDFC Regalia Gold",
    tier: "Premium Travel",
    active: true,
    image: "/cards/regalia-gold.png",
  },
  {
    name: "HSBC TravelOne",
    tier: "Premium Travel",
    active: true,
    image: "/cards/hsbc-travelone.jpg",
  },
  {
    name: "Amex Platinum Travel",
    tier: "Premium Travel",
    active: true,
    image: "/cards/amex-platinum-travel-v2.png",
  },
];

/**
 * The example wallet, shown as a static responsive grid (no carousel): every
 * card is visible at once, fitting within the viewport. Each tile is a fixed
 * landscape (credit-card) aspect ratio; the full card art is shown `contained`
 * on a dark plate so no logos or edges get cropped. Five-up on desktop, wrapping
 * down to two on mobile.
 */
export function SupportedCards() {
  return (
    <ul
      aria-label="Supported credit cards"
      className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5 lg:gap-5"
    >
      {CARDS.map((card) => (
        <li key={card.name}>
          <article className="group flex flex-col gap-3">
            <div className="relative aspect-[1.586/1] overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-card to-background p-2.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.06)] transition-all duration-500 group-hover:border-gold/40 group-hover:shadow-[inset_0_1px_0_rgba(255,255,255,0.1),0_20px_40px_-20px_rgba(0,0,0,0.55)]">
              <Image
                src={card.image}
                alt={card.name}
                fill
                sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 18vw"
                className="object-contain"
              />
            </div>
            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0">
                <p className="text-[0.65rem] uppercase tracking-[0.15em] text-muted-foreground/70">
                  {card.tier}
                </p>
                <p className="truncate font-heading text-sm text-foreground sm:text-base">
                  {card.name}
                </p>
              </div>
              {card.active ? (
                <Badge className="shrink-0 bg-gold text-gold-foreground hover:bg-gold/90">
                  Active
                </Badge>
              ) : (
                <Badge
                  variant="outline"
                  className="shrink-0 border-hairline bg-background/60 text-muted-foreground/80 backdrop-blur-sm"
                >
                  Coming soon
                </Badge>
              )}
            </div>
          </article>
        </li>
      ))}
    </ul>
  );
}
