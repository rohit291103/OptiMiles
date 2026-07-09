"use client";

import { useId, useState } from "react";
import { ArrowRight, Check, CreditCard } from "lucide-react";

import type { FinalRecommendation, RankedStrategy } from "@/lib/api";

/**
 * The explainable detail behind a recommendation — the "never a black box"
 * promise made visible. Every value here is a deterministic engine artifact
 * (score breakdown, simulated ledger, spend routing), not LLM output. Card ids
 * are resolved to names via the catalog map the simulator already fetched.
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

const SCORE_LABELS: { key: keyof RankedStrategy["score_breakdown"]; label: string }[] = [
  { key: "goal_achievement", label: "Goal achievement" },
  { key: "efficiency", label: "Efficiency" },
  { key: "cost", label: "Cost" },
  { key: "simplicity", label: "Simplicity" },
  { key: "portfolio_utilization", label: "Uses your cards" },
  { key: "risk", label: "Risk" },
];

export function StrategyDetail({
  rec,
  cardNames,
}: {
  rec: FinalRecommendation;
  cardNames: Map<string, string>;
}) {
  const recommended = rec.recommended;
  if (!recommended) return null;

  const nameOf = (id: string) => cardNames.get(id) ?? "Selected card";

  return (
    <div className="mt-6 space-y-6">
      <ScoreBreakdownBars breakdown={recommended.score_breakdown} score={recommended.score} />
      <ProgressChart strategy={recommended} />
      <SpendAllocation strategy={recommended} nameOf={nameOf} />
      {rec.narration?.action_items && rec.narration.action_items.length > 0 && (
        <ActionItems items={rec.narration.action_items} />
      )}
    </div>
  );
}

// ── Score breakdown ────────────────────────────────────────────────────────

function ScoreBreakdownBars({
  breakdown,
  score,
}: {
  breakdown: RankedStrategy["score_breakdown"];
  score: string;
}) {
  return (
    <section>
      <div className="flex items-baseline justify-between">
        <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
          Why this strategy scores {Math.round(Number(score))}
        </p>
      </div>
      <ul className="mt-3 space-y-2">
        {SCORE_LABELS.map(({ key, label }) => {
          const value = Math.max(0, Math.min(100, Number(breakdown[key])));
          return (
            <li key={key} className="flex items-center gap-3">
              <span className="w-32 shrink-0 text-sm text-muted-foreground">{label}</span>
              <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-input/40">
                <span
                  className="block h-full rounded-full bg-gold transition-all duration-700"
                  style={{ width: `${value}%` }}
                />
              </span>
              <span className="w-8 shrink-0 text-right text-xs tabular-nums text-foreground">
                {Math.round(value)}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

// ── Month-by-month accumulation (single-series line + area, gold hue) ──────

function ProgressChart({ strategy }: { strategy: RankedStrategy }) {
  const gradientId = useId();
  const [hover, setHover] = useState<number | null>(null);

  const ledger = strategy.simulation.ledger;
  if (ledger.length < 2) return null;

  // Cumulative reward points earned, month by month — the honest accumulation
  // curve. `points_earned_this_month` is the per-month earn delta (base +
  // category + milestone bonuses), so a single running sum is correct; it is
  // NOT the balance (which dips when a transfer fires), so the curve is
  // monotonic non-decreasing as real earning should be.
  const series = ledger.map((_, i) =>
    ledger.slice(0, i + 1).reduce((s, e) => s + e.points_earned_this_month, 0),
  );
  const max = Math.max(...series, 1);
  const W = 100;
  const H = 40;
  const n = series.length;
  const x = (i: number) => (n === 1 ? 0 : (i / (n - 1)) * W);
  const y = (v: number) => H - (v / max) * H;

  const linePath = series
    .map((v, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(2)} ${y(v).toFixed(2)}`)
    .join(" ");
  const areaPath = `${linePath} L ${W} ${H} L 0 ${H} Z`;

  return (
    <section>
      <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
        Points earned over {n} months
      </p>
      <div className="relative mt-3">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          preserveAspectRatio="none"
          className="h-24 w-full"
          role="img"
          aria-label={`Reward points accumulating over ${n} months, reaching ${max.toLocaleString()} points`}
        >
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--color-gold)" stopOpacity="0.35" />
              <stop offset="100%" stopColor="var(--color-gold)" stopOpacity="0" />
            </linearGradient>
          </defs>
          <path d={areaPath} fill={`url(#${gradientId})`} />
          <path
            d={linePath}
            fill="none"
            stroke="var(--color-gold)"
            strokeWidth="1.5"
            vectorEffect="non-scaling-stroke"
            strokeLinejoin="round"
            strokeLinecap="round"
          />
          {hover !== null && (
            <circle
              cx={x(hover)}
              cy={y(series[hover])}
              r="2.5"
              fill="var(--color-gold)"
              stroke="var(--color-background)"
              strokeWidth="1"
              vectorEffect="non-scaling-stroke"
            />
          )}
        </svg>
        {/* Hover hit-strips (one per month) over the plot. */}
        <div className="absolute inset-0 flex">
          {series.map((_, i) => (
            <button
              key={i}
              type="button"
              aria-label={`Month ${i}: ${series[i].toLocaleString()} points`}
              onMouseEnter={() => setHover(i)}
              onMouseLeave={() => setHover(null)}
              onFocus={() => setHover(i)}
              onBlur={() => setHover(null)}
              className="flex-1 focus:outline-none"
            />
          ))}
        </div>
        {hover !== null && (
          <div className="pointer-events-none mt-1 text-center text-xs text-muted-foreground">
            Month {hover}:{" "}
            <span className="tabular-nums text-foreground">
              {series[hover].toLocaleString()}
            </span>{" "}
            points
          </div>
        )}
      </div>
    </section>
  );
}

// ── Spend allocation (category → card) ─────────────────────────────────────

function SpendAllocation({
  strategy,
  nameOf,
}: {
  strategy: RankedStrategy;
  nameOf: (id: string) => string;
}) {
  const entries = Object.entries(strategy.strategy.spend_allocation);
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
            <span className="text-muted-foreground">
              {CATEGORY_LABELS[category] ?? category}
            </span>
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

// ── Action items ───────────────────────────────────────────────────────────

function ActionItems({
  items,
}: {
  items: { priority: number; action: string; impact: string | null }[];
}) {
  const sorted = [...items].sort((a, b) => a.priority - b.priority);
  return (
    <section>
      <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
        Your next steps
      </p>
      <ul className="mt-3 space-y-2.5 text-sm text-foreground/90">
        {sorted.map((item) => (
          <li key={`${item.priority}-${item.action}`} className="flex items-start gap-2.5">
            <span className="mt-0.5 grid size-5 shrink-0 place-items-center rounded-full bg-gold/15 text-gold">
              <Check className="size-3" />
            </span>
            <span>
              {item.action}
              {item.impact && (
                <span className="ml-1.5 text-xs text-gold">({item.impact})</span>
              )}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
