"use client";

import { CreditCard } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Carousel } from "@/components/ui/carousel";

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

export function SupportedCards() {
  return (
    <Carousel
      label="Supported credit cards"
      itemClassName="w-64 sm:w-72"
    >
      {CARDS.map((card) => (
        <article
          key={card.name}
          className="group relative h-44 overflow-hidden rounded-2xl border border-hairline bg-gradient-to-br from-card to-background p-5 ring-1 ring-foreground/5 transition-colors hover:border-gold/40"
        >
          <div className="absolute -right-8 -top-8 size-28 rounded-full bg-gold/10 blur-2xl transition-opacity group-hover:opacity-100 sm:opacity-60" />
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
    </Carousel>
  );
}
