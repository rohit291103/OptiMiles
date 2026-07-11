"use client";

import { useId, useState } from "react";
import { ArrowRight, Award, Check } from "lucide-react";

import type { SavedGoalDetail, SavedStrategy } from "@/lib/api";
import {
  CardsToAcquire,
  SpendRoutingDetailed,
  StrategyTiers,
  type StrategyTier,
} from "@/components/strategy-story";

/**
 * Renders a *persisted* recommendation — the stored engine artifacts behind a
 * saved goal (ledger, routing, transfers, milestones, action items), same
 * visual language as the live simulator's StrategyDetail. Nothing here is
 * recomputed; card/partner ids resolve through the response's name maps and
 * fall back to a generic label if a catalog id has since been retired.
 */

const SCORE_LABELS: {
  key: keyof NonNullable<SavedStrategy["score_breakdown"]>;
  label: string;
}[] = [
  { key: "goal_achievement", label: "Goal achievement" },
  { key: "efficiency", label: "Efficiency" },
  { key: "cost", label: "Cost" },
  { key: "simplicity", label: "Simplicity" },
  { key: "portfolio_utilization", label: "Uses your cards" },
  { key: "risk", label: "Risk" },
];

export function SavedStrategyView({ detail }: { detail: SavedGoalDetail }) {
  const strategy = detail.strategy;
  const cardName = (id: string) => detail.card_names[id] ?? "Card no longer listed";
  const partnerName = (id: string) =>
    detail.partner_names[id] ?? "Transfer partner";

  const tiers: StrategyTier[] = detail.strategy_options.map((o) => ({
    strategyId: o.strategy_id,
    headline: o.headline_differentiator,
    miles: o.miles_at_target_date,
    fees: o.total_fees_inr,
    cardsToAcquire: o.cards_to_acquire,
    isRecommended: o.is_recommended,
    coRecommended: o.co_recommended,
  }));

  return (
    <div className="space-y-8">
      {detail.summary && (
        <p className="max-w-2xl text-sm leading-relaxed text-foreground/90">
          {detail.summary}
        </p>
      )}

      <StrategyTiers
        tiers={tiers}
        targetMiles={detail.target_miles}
        nameOf={cardName}
      />

      {strategy && (
        <>
          {strategy.score_breakdown && (
            <ScoreBreakdownBars
              breakdown={strategy.score_breakdown}
              score={strategy.optimization_score}
            />
          )}
          <AccumulationChart strategy={strategy} />
          <SpendRoutingDetailed
            details={strategy.allocation_details}
            fallbackAllocation={strategy.spend_allocation}
            nameOf={cardName}
          />
          <CardsToAcquire ids={strategy.cards_to_acquire} nameOf={cardName} />
          {strategy.transfer_plan.length > 0 && (
            <TransferPlan
              strategy={strategy}
              cardName={cardName}
              partnerName={partnerName}
            />
          )}
          {strategy.milestones.length > 0 && (
            <Milestones strategy={strategy} cardName={cardName} />
          )}
        </>
      )}

      {detail.action_items.length > 0 && <ActionItems items={detail.action_items} />}

      {detail.reasoning && (
        <section>
          <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
            Why this works
          </p>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-foreground/80">
            {detail.reasoning}
          </p>
        </section>
      )}
    </div>
  );
}

// ── Score breakdown (persisted 6-part composite) ───────────────────────────

function ScoreBreakdownBars({
  breakdown,
  score,
}: {
  breakdown: NonNullable<SavedStrategy["score_breakdown"]>;
  score: string | null;
}) {
  return (
    <section>
      <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
        {score ? `Why this strategy scores ${Math.round(Number(score))}` : "Why this strategy"}
      </p>
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

// ── Accumulation chart (cumulative earn from the stored ledger) ────────────

function AccumulationChart({ strategy }: { strategy: SavedStrategy }) {
  const gradientId = useId();
  const [hover, setHover] = useState<number | null>(null);

  const ledger = strategy.ledger;
  if (ledger.length < 2) return null;

  // Cumulative points earned, month by month — same monotonic curve the live
  // simulator charts, rebuilt from the persisted per-month earn deltas.
  const series: number[] = [];
  let running = 0;
  for (const entry of ledger) {
    running += entry.points_earned_this_month;
    series.push(running);
  }
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
          className="h-28 w-full"
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

// ── Transfer plan ──────────────────────────────────────────────────────────

function TransferPlan({
  strategy,
  cardName,
  partnerName,
}: {
  strategy: SavedStrategy;
  cardName: (id: string) => string;
  partnerName: (id: string) => string;
}) {
  return (
    <section>
      <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
        When to transfer
      </p>
      <ul className="mt-3 space-y-2">
        {strategy.transfer_plan.map((step, i) => (
          <li
            key={`${step.from_card_id}-${step.planned_month}-${i}`}
            className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg border border-hairline bg-background/40 px-3 py-2.5 text-sm"
          >
            <span className="rounded-md bg-gold/15 px-2 py-0.5 text-xs font-medium tabular-nums text-gold">
              Month {step.planned_month}
            </span>
            <span className="text-foreground">
              {cardName(step.from_card_id)}
              <ArrowRight className="mx-1.5 inline size-3.5 text-gold" />
              {partnerName(step.to_partner_id)}
            </span>
            <span className="ml-auto tabular-nums text-muted-foreground">
              {step.points.toLocaleString("en-IN")} points
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

// ── Milestones ─────────────────────────────────────────────────────────────

function Milestones({
  strategy,
  cardName,
}: {
  strategy: SavedStrategy;
  cardName: (id: string) => string;
}) {
  return (
    <section>
      <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
        Milestone bonuses along the way
      </p>
      <ul className="mt-3 space-y-2">
        {strategy.milestones.map((m) => (
          <li
            key={m.milestone_id}
            className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg border border-hairline bg-background/40 px-3 py-2.5 text-sm"
          >
            <Award className="size-4 shrink-0 text-gold" />
            <span className="rounded-md bg-gold/15 px-2 py-0.5 text-xs font-medium tabular-nums text-gold">
              Month {m.expected_month}
            </span>
            <span className="text-foreground">{cardName(m.card_id)}</span>
            <span className="ml-auto tabular-nums text-muted-foreground">
              +{m.bonus_points.toLocaleString("en-IN")} points
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
  return (
    <section>
      <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
        Your next steps
      </p>
      <ul className="mt-3 space-y-2.5 text-sm text-foreground/90">
        {items.map((item) => (
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
