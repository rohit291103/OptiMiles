"use client";

import { useState } from "react";
import { ArrowRight, ChevronDown, CreditCard, Plus, Star } from "lucide-react";

import { cn } from "@/lib/utils";
import type { AllocationDetail } from "@/lib/api";

/**
 * Shared presentational pieces for the strategy "story" — used by both the live
 * simulator (strategy-detail.tsx) and the saved-goal view (saved-strategy.tsx).
 * They take normalized plain props, not a response type, so both callers feed
 * them the same shapes regardless of whether the data is live or persisted.
 *
 * Nothing here computes reward values — every number is an engine artifact
 * passed in. The per-category rows make the "why" visible (which card wins each
 * category and at what rate); the tier list tells the "your cards → +1 → +2"
 * comparison so the user reads the plan as a story, not a single black-box pick.
 */

const CATEGORY_LABELS: Record<string, string> = {
  travel: "Travel",
  dining: "Dining",
  online: "Online",
  groceries: "Groceries",
  utilities: "Utilities",
  fuel: "Fuel",
  international: "International",
  default: "Everything else",
};

function categoryLabel(slug: string): string {
  return CATEGORY_LABELS[slug] ?? slug.charAt(0).toUpperCase() + slug.slice(1);
}

function inr(n: number): string {
  return `₹${n.toLocaleString("en-IN")}`;
}

// ── Tier comparison: "your cards → +1 → +2" ────────────────────────────────

export type StrategyTier = {
  strategyId: string;
  headline: string;
  miles: number;
  fees: number;
  cardsToAcquire: string[];
  isRecommended: boolean;
  coRecommended?: boolean;
};

/**
 * The comparison story. Shows each option as a row: what it reaches, what it
 * costs, and what (if anything) you'd add. The recommended one is marked. When
 * there's only one option, renders nothing (there's no story to compare).
 */
export function StrategyTiers({
  tiers,
  targetMiles,
  nameOf,
}: {
  tiers: StrategyTier[];
  targetMiles: number;
  nameOf: (id: string) => string;
}) {
  if (tiers.length < 2) return null;
  const maxMiles = Math.max(...tiers.map((t) => t.miles), targetMiles, 1);

  return (
    <section>
      <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
        Your options, compared
      </p>
      <ul className="mt-3 space-y-2.5">
        {tiers.map((tier) => {
          const reaches = tier.miles >= targetMiles;
          return (
            <li
              key={tier.strategyId}
              className={cn(
                "rounded-xl border bg-background/40 p-3.5 sm:p-4",
                tier.isRecommended
                  ? "border-gold/40 bg-gold/6"
                  : "border-hairline",
              )}
            >
              <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1.5">
                <span className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-sm font-medium text-foreground">
                  {tier.isRecommended && (
                    <Star className="size-3.5 shrink-0 fill-gold text-gold" />
                  )}
                  <span className="min-w-0 break-words">
                    {tier.cardsToAcquire.length === 0
                      ? "With your current cards"
                      : `Add ${tier.cardsToAcquire.map(nameOf).join(" + ")}`}
                  </span>
                  {tier.isRecommended && (
                    <span className="shrink-0 rounded-full bg-gold/15 px-2 py-0.5 text-[10px] uppercase tracking-wide text-gold">
                      Recommended
                    </span>
                  )}
                </span>
                <span className="shrink-0 text-xs capitalize text-muted-foreground">
                  {tier.headline}
                </span>
              </div>

              <div className="mt-2.5 flex items-center gap-3">
                <span className="h-2 flex-1 overflow-hidden rounded-full bg-input/40">
                  <span
                    className={cn(
                      "block h-full rounded-full",
                      reaches ? "bg-gold" : "bg-muted-foreground/50",
                    )}
                    style={{ width: `${Math.min(100, (tier.miles / maxMiles) * 100)}%` }}
                  />
                </span>
                <span className="shrink-0 text-sm tabular-nums font-medium text-foreground">
                  {tier.miles.toLocaleString("en-IN")} mi
                </span>
              </div>
              <p className="mt-1.5 text-xs text-muted-foreground">
                {reaches ? "Reaches your goal" : "Falls short of your goal"}
                {" · "}
                {tier.fees === 0 ? "no annual fee" : `${inr(tier.fees)} in fees`}
              </p>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

// ── Per-category routing with the earn "why" ───────────────────────────────

/**
 * "Where to spend," but explained: each category shows its monthly spend, which
 * card earns it, the rate, and the projected monthly points. Rows group under
 * the card so "everything on one card" reads as a deliberate choice with the
 * rate visible, and genuine splits show naturally. Falls back to the plain
 * category→card map when per-category detail isn't available (older saves).
 */
export function SpendRoutingDetailed({
  details,
  fallbackAllocation,
  nameOf,
}: {
  details: AllocationDetail[];
  fallbackAllocation?: Record<string, string>;
  nameOf: (id: string) => string;
}) {
  const [open, setOpen] = useState<string | null>(null);

  if (details.length === 0) {
    if (!fallbackAllocation) return null;
    const entries = Object.entries(fallbackAllocation);
    if (entries.length === 0) return null;
    return (
      <section>
        <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
          Where to spend
        </p>
        <ul className="mt-3 space-y-2">
          {entries.map(([category, cardId]) => (
            <li
              key={category}
              className="flex items-center justify-between rounded-lg border border-hairline bg-background/40 px-3 py-2 text-sm"
            >
              <span className="text-muted-foreground">{categoryLabel(category)}</span>
              <span className="flex items-center gap-1.5 font-medium text-foreground">
                <ArrowRight className="size-3.5 text-gold" />
                <CreditCard className="size-3.5 text-gold" />
                {nameOf(cardId)}
              </span>
            </li>
          ))}
        </ul>
      </section>
    );
  }

  // Group the per-category rows by card, so the story reads "put X, Y, Z on
  // this card because it earns them best."
  const byCard = new Map<string, AllocationDetail[]>();
  for (const d of details) {
    const list = byCard.get(d.card_id) ?? [];
    list.push(d);
    byCard.set(d.card_id, list);
  }

  // A card's honest monthly points is the exact cross-category sum floored
  // ONCE — matching the engine (one floor per card-month), NOT the sum of the
  // per-category rows' already-floored `monthly_points` (which can undershoot
  // by a point or two when categories share a card).
  const cardMonthlyPoints = (rows: AllocationDetail[]): number =>
    Math.floor(
      rows.reduce((s, r) => s + (r.monthly_spend_inr * Number(r.earn_rate)) / 100, 0),
    );

  return (
    <section>
      <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
        Where to spend, and why
      </p>
      <div className="mt-3 space-y-3">
        {[...byCard.entries()].map(([cardId, rows]) => {
          const cardTotal = cardMonthlyPoints(rows);
          return (
            <div
              key={cardId}
              className="overflow-hidden rounded-xl border border-hairline bg-background/40"
            >
              <div className="flex items-center justify-between gap-3 border-b border-hairline/70 px-3.5 py-2.5">
                <span className="flex min-w-0 items-center gap-2 text-sm font-medium text-foreground">
                  <CreditCard className="size-4 shrink-0 text-gold" />
                  <span className="truncate">{nameOf(cardId)}</span>
                </span>
                <span className="shrink-0 text-xs tabular-nums text-muted-foreground">
                  ~{cardTotal.toLocaleString("en-IN")} pts/mo
                </span>
              </div>
              <ul className="divide-y divide-hairline/50">
                {rows.map((r) => {
                  const hasNotes = r.notes.length > 0;
                  const rowOpen = open === `${cardId}:${r.category_slug}`;
                  return (
                    <li key={r.category_slug} className="px-3.5 py-2.5 text-sm">
                      <div className="flex items-center justify-between gap-3">
                        <span className="min-w-0 truncate text-foreground">
                          {categoryLabel(r.category_slug)}
                          <span className="ml-2 text-xs text-muted-foreground">
                            {inr(r.monthly_spend_inr)}/mo
                          </span>
                        </span>
                        <span className="flex shrink-0 items-center gap-2 text-xs tabular-nums text-muted-foreground">
                          <span className="text-gold">{Number(r.earn_rate)}×</span>
                          <span className="text-foreground">
                            {r.monthly_points.toLocaleString("en-IN")} pts/mo
                          </span>
                          {hasNotes && (
                            <button
                              type="button"
                              aria-label={`Why ${categoryLabel(r.category_slug)} earns this rate`}
                              aria-expanded={rowOpen}
                              onClick={() =>
                                setOpen(rowOpen ? null : `${cardId}:${r.category_slug}`)
                              }
                              className="grid size-5 place-items-center rounded text-muted-foreground transition-colors hover:text-foreground"
                            >
                              <ChevronDown
                                className={cn(
                                  "size-3.5 transition-transform",
                                  rowOpen && "rotate-180",
                                )}
                              />
                            </button>
                          )}
                        </span>
                      </div>
                      {hasNotes && rowOpen && (
                        <ul className="mt-2 space-y-1 border-l border-gold/30 pl-3 text-xs text-muted-foreground">
                          {r.notes.map((note, i) => (
                            <li key={i}>{note}</li>
                          ))}
                        </ul>
                      )}
                    </li>
                  );
                })}
              </ul>
            </div>
          );
        })}
      </div>
    </section>
  );
}

// ── Cards to acquire (shared chip row) ─────────────────────────────────────

export function CardsToAcquire({
  ids,
  nameOf,
}: {
  ids: string[];
  nameOf: (id: string) => string;
}) {
  if (ids.length === 0) return null;
  return (
    <section>
      <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
        Cards to add
      </p>
      <ul className="mt-3 flex flex-wrap gap-2">
        {ids.map((id) => (
          <li
            key={id}
            className="flex items-center gap-1.5 rounded-full border border-gold/40 bg-gold/10 px-3.5 py-1.5 text-xs font-medium text-gold"
          >
            <Plus className="size-3.5" /> {nameOf(id)}
          </li>
        ))}
      </ul>
    </section>
  );
}
