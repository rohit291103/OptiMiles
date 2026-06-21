"use client";

import * as React from "react";
import { CreditCard } from "lucide-react";

import { Badge } from "@/components/ui/badge";

const CARDS = [
  { name: "HDFC Infinia", tier: "Premium Travel", active: true },
  { name: "HDFC Diners Club Black", tier: "Premium Travel", active: true },
  { name: "Axis Magnus", tier: "Premium Travel", active: true },
  { name: "Axis Atlas", tier: "Premium Travel", active: true },
  { name: "Amex Platinum Travel", tier: "Premium Travel", active: true },
  { name: "SBI Cashback", tier: "Mid-Tier Reward", active: true },
  { name: "Amex MRCC", tier: "Premium Travel", active: false },
  { name: "ICICI Emeralde", tier: "Premium Travel", active: false },
  { name: "HDFC Regalia Gold", tier: "Mid-Tier Reward", active: false },
  { name: "IDFC First Wealth", tier: "Mid-Tier Reward", active: false },
  { name: "Air India SBI Signature", tier: "Airline / Travel", active: false },
  { name: "Vistara SBI Prime", tier: "Airline / Travel", active: false },
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
            className={`group relative h-44 w-64 shrink-0 overflow-hidden rounded-2xl border bg-linear-to-br from-card to-background p-5 ring-1 ring-foreground/5 transition-all duration-500 sm:w-72 ${
              i === activeIndex
                ? "scale-[1.03] border-gold/40"
                : "scale-100 border-hairline opacity-80"
            }`}
          >
            <div className="absolute -right-8 -top-8 size-28 rounded-full bg-gold/10 blur-2xl" />
            <div className="relative flex h-full flex-col justify-between">
              <div className="flex items-start justify-between">
                <CreditCard className="size-7 text-gold" />
                {card.active ? (
                  <Badge className="bg-gold text-gold-foreground hover:bg-gold/90">
                    Active
                  </Badge>
                ) : (
                  <Badge
                    variant="outline"
                    className="border-hairline text-muted-foreground/70"
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
