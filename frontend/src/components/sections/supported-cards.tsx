"use client";

import * as React from "react";
import Image from "next/image";
import { CreditCard } from "lucide-react";

import { Badge } from "@/components/ui/badge";

type Card = {
  name: string;
  tier: string;
  active: boolean;
  /** Path under /public, e.g. "/cards/infinia.png". Cards without a photo
   * fall back to the icon + gradient treatment. */
  image?: string;
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
];

/**
 * Premium autoplay carousel for supported cards: slow auto-scroll every 4s,
 * pause on hover/drag/focus, drag + touch support, and a subtle scale on the
 * card nearest the viewport centre. Dependency-free (no embla/swiper).
 */
export function SupportedCards() {
  const scrollerRef = React.useRef<HTMLDivElement>(null);
  const [paused, setPaused] = React.useState(false);
  const [activeIndex, setActiveIndex] = React.useState(0);

  // Track which card is closest to the centre of the scroller for the scale cue.
  const updateActive = React.useCallback(() => {
    const el = scrollerRef.current;
    if (!el) return;
    const centre = el.scrollLeft + el.clientWidth / 2;
    let nearest = 0;
    let nearestDist = Infinity;
    Array.from(el.children).forEach((child, i) => {
      const node = child as HTMLElement;
      const childCentre = node.offsetLeft + node.offsetWidth / 2;
      const dist = Math.abs(childCentre - centre);
      if (dist < nearestDist) {
        nearestDist = dist;
        nearest = i;
      }
    });
    setActiveIndex(nearest);
  }, []);

  React.useEffect(() => {
    const el = scrollerRef.current;
    if (!el) return;
    updateActive();
    el.addEventListener("scroll", updateActive, { passive: true });
    return () => el.removeEventListener("scroll", updateActive);
  }, [updateActive]);

  // Autoplay: advance ~one card every 4s, looping back to the start at the end.
  React.useEffect(() => {
    if (paused) return;
    const reduced = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;
    if (reduced) return;

    const id = window.setInterval(() => {
      const el = scrollerRef.current;
      if (!el) return;
      const step = (el.firstElementChild as HTMLElement)?.offsetWidth ?? 280;
      const atEnd = el.scrollLeft + el.clientWidth >= el.scrollWidth - 8;
      el.scrollTo({
        left: atEnd ? 0 : el.scrollLeft + step + 16,
        behavior: "smooth",
      });
    }, 4000);
    return () => window.clearInterval(id);
  }, [paused]);

  // Pointer drag-to-scroll.
  const drag = React.useRef({ active: false, startX: 0, startScroll: 0 });

  function onPointerDown(e: React.PointerEvent<HTMLDivElement>) {
    const el = scrollerRef.current;
    if (!el) return;
    drag.current = {
      active: true,
      startX: e.clientX,
      startScroll: el.scrollLeft,
    };
    setPaused(true);
  }
  function onPointerMove(e: React.PointerEvent<HTMLDivElement>) {
    if (!drag.current.active) return;
    const el = scrollerRef.current;
    if (!el) return;
    el.scrollLeft = drag.current.startScroll - (e.clientX - drag.current.startX);
  }
  function endDrag() {
    drag.current.active = false;
  }

  return (
    <div
      role="region"
      aria-label="Supported credit cards"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => {
        setPaused(false);
        endDrag();
      }}
      onFocusCapture={() => setPaused(true)}
      onBlurCapture={() => setPaused(false)}
    >
      <div
        ref={scrollerRef}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        className="flex cursor-grab gap-4 overflow-x-auto scroll-smooth pb-4 select-none active:cursor-grabbing [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        {CARDS.map((card, i) => (
          <article
            key={card.name}
            className={`group relative h-48 w-64 shrink-0 overflow-hidden rounded-[1.75rem] border bg-linear-to-br from-card to-background p-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] transition-all duration-500 sm:w-72 ${
              i === activeIndex
                ? "scale-[1.04] border-gold/40 shadow-[inset_0_1px_0_rgba(255,255,255,0.1),0_20px_40px_-20px_rgba(0,0,0,0.5)]"
                : "scale-100 border-white/10 opacity-80"
            }`}
          >
            {card.image ? (
              <>
                <Image
                  src={card.image}
                  alt={card.name}
                  fill
                  sizes="(max-width: 640px) 16rem, 18rem"
                  draggable={false}
                  className="object-cover"
                />
                {/* Darkening scrim so the label stays legible over the art */}
                <div className="absolute inset-0 bg-linear-to-t from-background/90 via-background/30 to-background/10" />
              </>
            ) : (
              <div className="absolute -right-8 -top-8 size-28 rounded-full bg-gold/10 blur-2xl" />
            )}
            <div className="relative flex h-full flex-col justify-between">
              <div className="flex items-start justify-between">
                {card.image ? (
                  <span />
                ) : (
                  <CreditCard className="size-7 text-gold" />
                )}
                {card.active ? (
                  <Badge className="bg-gold text-gold-foreground hover:bg-gold/90">
                    Active
                  </Badge>
                ) : (
                  <Badge
                    variant="outline"
                    className="border-hairline bg-background/60 text-muted-foreground/80 backdrop-blur-sm"
                  >
                    Coming soon
                  </Badge>
                )}
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.15em] text-muted-foreground/70">
                  {card.tier}
                </p>
                <p className="mt-1 font-heading text-lg text-foreground">
                  {card.name}
                </p>
              </div>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
