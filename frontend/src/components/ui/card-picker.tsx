"use client";

import { Check } from "lucide-react";

import type { CardSummary } from "@/lib/api";

/** Stable bank-grouped ordering — catalog order, first-seen bank first. */
export function groupByBank(cards: CardSummary[]): [string, CardSummary[]][] {
  const groups: [string, CardSummary[]][] = [];
  for (const card of cards) {
    const group = groups.find(([bank]) => bank === card.bank);
    if (group) group[1].push(card);
    else groups.push([card.bank, [card]]);
  }
  return groups;
}

/**
 * Bank-grouped wallet picker, shared between the goal wizard and Best Card.
 *
 * Extracted from `goal-wizard.tsx` (roadmap Phase 1): Best Card is available
 * signed-out with a REAL picker rather than a demo wallet, so both surfaces
 * must present the same wallet in the same way — one component, not two that
 * drift.
 */
export function CardPicker({
  cards,
  selectedIds,
  onToggle,
}: {
  cards: CardSummary[];
  selectedIds: string[];
  onToggle: (cardId: string) => void;
}) {
  return (
    <div className="grid gap-x-8 gap-y-5 sm:grid-cols-2">
      {groupByBank(cards).map(([bank, bankCards]) => (
        <div key={bank}>
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground/80">
            {bank}
          </p>
          <div className="mt-2.5 flex flex-wrap gap-2">
            {bankCards.map((card) => {
              const selected = selectedIds.includes(card.id);
              return (
                <button
                  key={card.id}
                  type="button"
                  onClick={() => onToggle(card.id)}
                  aria-pressed={selected}
                  className={`flex min-h-11 items-center gap-2 rounded-xl border px-3.5 py-2 text-sm font-medium transition-all sm:min-h-0 ${
                    selected
                      ? "border-gold/50 bg-gold/10 text-gold"
                      : "border-hairline bg-input/20 text-muted-foreground hover:border-white/25 hover:text-foreground"
                  }`}
                >
                  <span
                    aria-hidden="true"
                    className={`grid size-4 shrink-0 place-items-center rounded-full border transition-colors ${
                      selected
                        ? "border-gold bg-gold text-gold-foreground"
                        : "border-white/25 text-transparent"
                    }`}
                  >
                    <Check className="size-3" strokeWidth={3} />
                  </span>
                  {card.card_name}
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
