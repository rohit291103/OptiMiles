"use client";

import { useEffect, useState } from "react";
import { CreditCard, Landmark } from "lucide-react";

import { fetchCards, type CardSummary } from "@/lib/api";

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
          <div className="mt-3 grid gap-4 sm:grid-cols-2">
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
  return (
    <div className="rounded-xl border border-hairline bg-card/50 p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <span className="grid size-9 shrink-0 place-items-center rounded-lg border border-gold/30 bg-gold/10 text-gold">
            <CreditCard className="size-4" />
          </span>
          <h3 className="font-medium text-foreground">{card.card_name}</h3>
        </div>
        {!card.acquirable && (
          <span className="shrink-0 rounded-full border border-hairline px-2 py-0.5 text-[11px] uppercase tracking-wide text-muted-foreground">
            Existing holders
          </span>
        )}
      </div>
      <dl className="mt-4 flex flex-wrap gap-x-6 gap-y-1 text-sm">
        <div className="flex items-baseline gap-1.5">
          <dt className="text-xs text-muted-foreground">Annual fee</dt>
          <dd className="tabular-nums text-foreground">
            {card.annual_fee_inr === 0
              ? "Free"
              : `₹${card.annual_fee_inr.toLocaleString("en-IN")}`}
          </dd>
        </div>
        <div className="flex items-baseline gap-1.5">
          <dt className="text-xs text-muted-foreground">Lounge access</dt>
          <dd className="text-foreground">{card.has_lounge_access ? "Yes" : "No"}</dd>
        </div>
      </dl>
    </div>
  );
}
