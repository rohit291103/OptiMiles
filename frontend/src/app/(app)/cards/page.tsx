"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { CreditCard, Landmark } from "lucide-react";

import { fetchCards, type CardSummary } from "@/lib/api";

/**
 * Card art, keyed by "bank|card_name" (CardSummary has no slug/image field —
 * this mirrors the same real filenames the landing page's curated wallet
 * uses, see supported-cards.tsx). Cards without sourced art fall back to the
 * generic icon rather than a broken image.
 */
const CARD_IMAGES: Record<string, string> = {
  "HDFC|Infinia Metal": "/cards/infinia.png",
  "HDFC|Diners Club Black Metal": "/cards/diners-black.png",
  "HDFC|Regalia Gold": "/cards/regalia-gold.png",
  "HSBC|TravelOne": "/cards/hsbc-travelone.jpg",
  "Amex|Platinum Travel": "/cards/amex-platinum-travel-v2.png",
  "Amex|Platinum Charge": "/cards/amex-platinum-charge-v2.png",
  "Axis|Atlas": "/cards/axis-atlas-v2.png",
  "Axis|Magnus for Burgundy": "/cards/axis-magnus-v2.png",
};

// Display-name overrides — cosmetic only, doesn't touch the engine's catalog.
const CARD_DISPLAY_NAMES: Record<string, string> = {
  "Axis|Magnus for Burgundy": "Magnus Burgandy",
};

// SBI Cashback is a deliberate seed row (a cashback-only negative case for the
// Valuation Engine, see backend/app/valuation/opportunities.py) — real, but
// not a travel-reward card, so it's hidden from this reward-focused catalog.
const HIDDEN_CARDS = new Set(["SBI|Cashback"]);

/**
 * The supported-card catalog, inside the app shell — every card the engine
 * can reason about, straight from GET /catalog/cards (the same live source the
 * simulator's wallet picker uses). Read-only; a future "my wallet" lives here.
 */

type LoadState =
  | { phase: "loading" }
  | { phase: "ready"; cards: CardSummary[] }
  | { phase: "error"; message: string };

export default function CardsPage() {
  const [state, setState] = useState<LoadState>({ phase: "loading" });

  useEffect(() => {
    let active = true;
    fetchCards()
      .then((cards) => {
        if (active) setState({ phase: "ready", cards });
      })
      .catch((e) => {
        if (active)
          setState({
            phase: "error",
            message: e instanceof Error ? e.message : "Couldn't load the catalog.",
          });
      });
    return () => {
      active = false;
    };
  }, []);

  if (state.phase === "loading") {
    return (
      <p className="text-sm text-muted-foreground" role="status">
        Loading the card catalog…
      </p>
    );
  }

  if (state.phase === "error") {
    return (
      <div className="rounded-xl border border-destructive/40 bg-destructive/5 p-4">
        <p className="text-sm text-destructive" role="alert">
          {state.message}
        </p>
      </div>
    );
  }

  // Group by bank so the catalog reads as a portfolio, not a flat dump.
  const byBank = new Map<string, CardSummary[]>();
  for (const card of state.cards) {
    if (HIDDEN_CARDS.has(`${card.bank}|${card.card_name}`)) continue;
    const group = byBank.get(card.bank) ?? [];
    group.push(card);
    byBank.set(card.bank, group);
  }

  return (
    <div className="space-y-8">
      <p className="max-w-2xl text-sm text-muted-foreground">
        Every card the strategy engine can reason about today — earn rates,
        transfer partners, milestones and caps, all verified against published
        sources.
      </p>
      {[...byBank.entries()].map(([bank, cards]) => (
        <section key={bank}>
          <h2 className="flex items-center gap-2 text-xs uppercase tracking-[0.12em] text-muted-foreground">
            <Landmark className="size-3.5 text-gold" /> {bank}
          </h2>
          <div className="mt-3 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
            {cards.map((card) => (
              <CardTile key={card.id} card={card} />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

function CardTile({ card }: { card: CardSummary }) {
  const image = CARD_IMAGES[`${card.bank}|${card.card_name}`];
  const displayName = CARD_DISPLAY_NAMES[`${card.bank}|${card.card_name}`] ?? card.card_name;
  return (
    <article className="group flex flex-col gap-3">
      <div className="relative aspect-[1.586/1] overflow-hidden rounded-2xl bg-black shadow-[0_1px_0_rgba(255,255,255,0.04)] ring-1 ring-white/5 transition-all duration-500 group-hover:ring-gold/40 group-hover:shadow-[0_20px_40px_-20px_rgba(0,0,0,0.55)]">
        {image ? (
          // Real card art fills the tile edge-to-edge (the photos are already
          // full card faces), so no plate/padding shows a light frame around
          // dark cards like Magnus.
          <Image
            src={image}
            alt={displayName}
            fill
            sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 22vw"
            className="object-cover"
          />
        ) : (
          <span className="grid size-full place-items-center bg-gradient-to-br from-card to-background text-gold">
            <CreditCard className="size-8" />
          </span>
        )}
        {!card.acquirable && (
          <span className="absolute right-2 top-2 rounded-full border border-hairline bg-background/70 px-2 py-0.5 text-[10px] uppercase tracking-wide text-muted-foreground backdrop-blur-sm">
            Existing holders
          </span>
        )}
      </div>
      <div>
        <p className="truncate font-heading text-sm text-foreground sm:text-base">
          {displayName}
        </p>
        <p className="mt-0.5 text-xs tabular-nums text-muted-foreground">
          {card.annual_fee_inr === 0
            ? "Free"
            : `₹${card.annual_fee_inr.toLocaleString("en-IN")}/yr`}
          {card.has_lounge_access ? " · Lounge access" : ""}
        </p>
      </div>
    </article>
  );
}
