"use client";

import { useId, useState } from "react";
import {
  ArrowRight,
  Award,
  BadgeCheck,
  ChevronDown,
  CreditCard,
  Info,
  Plane,
  Plus,
  Star,
} from "lucide-react";

import { cn } from "@/lib/utils";
import type { AllocationDetail, ScoreBreakdown } from "@/lib/api";

/**
 * The strategy narrative — shared by the live simulator (strategy-detail.tsx)
 * and the saved-goal view (saved-strategy.tsx). Reads top-to-bottom like a
 * route plan: verdict first, then the options as switchable tabs, then the
 * selected option's plan as numbered steps (get cards → spend → transfer →
 * book), then a plain-language "why", with the raw scoring machinery demoted
 * to a disclosure.
 *
 * Nothing here computes reward values — every mile/point/fee is an engine
 * artifact passed in. The only arithmetic is presentation (differences,
 * percentages of engine numbers), matching the "LLMs and UIs never do reward
 * math" boundary.
 */

// ── Shared vocabulary ───────────────────────────────────────────────────────

const CATEGORY_LABELS: Record<string, string> = {
  travel: "Travel",
  dining: "Dining",
  online: "Online shopping",
  groceries: "Groceries",
  utilities: "Utilities",
  fuel: "Fuel",
  international: "International",
  default: "Everything else",
};

export function categoryLabel(slug: string): string {
  return CATEGORY_LABELS[slug] ?? slug.charAt(0).toUpperCase() + slug.slice(1);
}

function inr(n: number): string {
  return `₹${n.toLocaleString("en-IN")}`;
}

function fmt(n: number): string {
  return n.toLocaleString("en-IN");
}

// ── 1. Verdict — the answer, in English, before anything else ──────────────

export function VerdictHero({
  feasible,
  tight,
  targetMiles,
  projectedMiles,
  goalMonth,
  horizonMonths,
  newFees,
  cardsToAcquireNames,
  programName,
  narrationSummary,
}: {
  feasible: boolean;
  tight: boolean;
  targetMiles: number;
  projectedMiles: number;
  goalMonth: number | null;
  horizonMonths: number | null;
  newFees: number;
  cardsToAcquireNames: string[];
  programName: string;
  narrationSummary?: string | null;
}) {
  const monthsEarly =
    goalMonth !== null && horizonMonths !== null ? horizonMonths - goalMonth : null;

  let headline: string;
  if (!feasible) {
    headline = `As stated, this goal doesn't reach ${fmt(targetMiles)} ${programName} miles in time — here's what would make it work.`;
  } else if (goalMonth !== null) {
    const timing =
      monthsEarly !== null && monthsEarly > 0
        ? ` — ${monthsEarly === 1 ? "a month" : `${monthsEarly} months`} ahead of your deadline`
        : " — right on your deadline";
    headline = `You'll have ~${fmt(projectedMiles)} ${programName} miles by month ${goalMonth}${timing}.`;
  } else {
    headline = `This plan projects ~${fmt(projectedMiles)} ${programName} miles against your ${fmt(targetMiles)} target.`;
  }

  const how =
    cardsToAcquireNames.length === 0
      ? "with the cards you already hold"
      : `after adding ${cardsToAcquireNames.join(" and ")}`;
  const cost =
    newFees === 0 ? "₹0 in new card fees" : `${inr(newFees)} in card fees`;

  return (
    <section
      className={cn(
        "rounded-2xl border p-5 sm:p-6",
        feasible ? "border-gold/30 bg-gold/5" : "border-hairline bg-background/40",
      )}
    >
      <p className="flex items-center gap-2 text-xs uppercase tracking-[0.12em] text-muted-foreground">
        {feasible ? (
          <BadgeCheck className="size-4 text-gold" />
        ) : (
          <Info className="size-4 text-muted-foreground" />
        )}
        {feasible ? (tight ? "Achievable — cutting it close" : "Achievable") : "Not as stated"}
      </p>
      <h4 className="mt-2.5 max-w-2xl font-heading text-xl leading-snug text-foreground sm:text-2xl">
        {headline}
      </h4>
      {feasible && (
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          You need {fmt(targetMiles)} miles for this trip. The recommended route gets
          there {how}, for {cost}.
        </p>
      )}
      {/* When the plan is feasible the headline above already states the
          answer with the same numbers — repeating the narration summary read
          as a stylistic inconsistency, not information. It only adds value on
          the infeasible path (the adjustment story). */}
      {!feasible && narrationSummary && (
        <p className="mt-3 max-w-2xl border-t border-hairline/60 pt-3 text-sm leading-relaxed text-foreground/85">
          {narrationSummary}
        </p>
      )}
    </section>
  );
}

// ── 2. The options, as tabs — picking one swaps the whole plan below ───────

export type PlanTierDetail = {
  allocationDetails: AllocationDetail[];
  fallbackAllocation?: Record<string, string>;
  transferPlan: { fromCardId: string; toPartnerId: string; points: number; plannedMonth: number }[];
  milestones: { id: string; cardId: string; expectedMonth: number; bonusPoints: number }[];
  ledger: { month: number; pointsEarned: number }[];
  scoreBreakdown: ScoreBreakdown | null;
  score: string | null;
};

export type PlanTier = {
  strategyId: string;
  miles: number;
  /** New-card joining fees — the number the user reads as "what this route
   * costs me". Transfer/program micro-fees live in `transferFees`. */
  fees: number;
  /** Bank program fees paid at transfer time across the plan (e.g. Axis
   * ₹235/transfer) — mentioned once in the transfer step, never headlined. */
  transferFees: number;
  monthsToGoal: number | null;
  cardsToAcquire: string[];
  isRecommended: boolean;
  /** e.g. "fastest" / "lowest fees" / "balanced" — the engine's own
   * differentiator, used to disambiguate tabs whose card labels collide
   * (two different archetypes can both land on "Add Magnus for Burgundy"
   * with different numbers underneath). */
  headline: string;
  /** Full plan payload — present for every tier on live runs; only for the
   * recommended tier on older saved goals (the rest persisted compactly). */
  detail: PlanTierDetail | null;
};

/** Base label + a headline suffix when another tier shares the same label —
 * "Add Magnus for Burgundy" appearing twice (two archetypes converging on
 * the same card) reads as a duplicate unless disambiguated. */
function tierLabel(tier: PlanTier, allTiers: PlanTier[], nameOf: (id: string) => string): string {
  const base =
    tier.cardsToAcquire.length === 0
      ? "Your current cards"
      : `Add ${tier.cardsToAcquire.map(nameOf).join(" + ")}`;
  const collides = allTiers.some(
    (t) =>
      t.strategyId !== tier.strategyId &&
      (t.cardsToAcquire.length === 0) === (tier.cardsToAcquire.length === 0) &&
      t.cardsToAcquire.join() === tier.cardsToAcquire.join(),
  );
  return collides && tier.headline ? `${base} (${tier.headline})` : base;
}

/** One sentence comparing the selected tier against the recommended one —
 * plain-language trade-off instead of a wall of bars. Pure differences of
 * engine numbers. */
function tradeOff(selected: PlanTier, recommended: PlanTier): string | null {
  if (selected.strategyId === recommended.strategyId) return null;
  const milesDiff = selected.miles - recommended.miles;
  const feesDiff = selected.fees - recommended.fees;
  const milesPart =
    milesDiff === 0
      ? "earns the same miles as the recommended route"
      : milesDiff > 0
        ? `earns ${fmt(milesDiff)} more miles than the recommended route`
        : `earns ${fmt(-milesDiff)} fewer miles than the recommended route`;
  const feesPart =
    feesDiff === 0
      ? "for the same fees"
      : feesDiff > 0
        ? `but costs ${inr(feesDiff)} more in card fees`
        : `and saves ${inr(-feesDiff)} in fees`;
  return `This route ${milesPart}, ${feesPart}. ${
    milesDiff > 0
      ? "Worth it if you want a buffer for taxes, upgrades or a second trip — not needed to reach this goal."
      : "We recommend the marked option instead."
  }`;
}

export function StrategyPlanTabs({
  tiers,
  targetMiles,
  horizonMonths,
  programName,
  chartMilesPerSeat,
  bufferMiles,
  risks,
  reasoning,
  comparisonNotes,
  nameOf,
  partnerNameOf,
  preferNoNewCards = false,
}: {
  tiers: PlanTier[];
  targetMiles: number;
  horizonMonths: number | null;
  programName: string;
  chartMilesPerSeat?: number | null;
  bufferMiles?: number | null;
  risks: string[];
  reasoning?: string | null;
  comparisonNotes?: string | null;
  nameOf: (id: string) => string;
  partnerNameOf: (id: string) => string;
  preferNoNewCards?: boolean;
}) {
  const recommended = tiers.find((t) => t.isRecommended) ?? tiers[0];
  const preferred = preferNoNewCards
    ? (tiers.find((t) => t.cardsToAcquire.length === 0) ?? recommended)
    : recommended;
  const [selectedId, setSelectedId] = useState(preferred?.strategyId);
  const selected = tiers.find((t) => t.strategyId === selectedId) ?? recommended;

  if (tiers.length === 0 || !selected) return null;

  const note = tradeOff(selected, recommended);

  return (
    <div className="space-y-5">
      {tiers.length > 1 && (
        <section aria-label="Compare your route options">
          <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
            Your routes — pick one to see its full plan
          </p>
          <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3" role="tablist">
            {tiers.map((tier) => {
              const active = tier.strategyId === selected.strategyId;
              const reaches = tier.miles >= targetMiles;
              return (
                <button
                  key={tier.strategyId}
                  type="button"
                  role="tab"
                  aria-selected={active}
                  onClick={() => setSelectedId(tier.strategyId)}
                  className={cn(
                    "rounded-xl border p-3.5 text-left transition-colors",
                    active
                      ? "border-gold/50 bg-gold/8"
                      : "border-hairline bg-background/40 hover:border-gold/25",
                  )}
                >
                  <span className="flex items-start justify-between gap-2">
                    <span className="min-w-0 break-words text-sm font-medium text-foreground">
                      {tierLabel(tier, tiers, nameOf)}
                    </span>
                    {tier.isRecommended && (
                      <Star className="mt-0.5 size-3.5 shrink-0 fill-gold text-gold" />
                    )}
                  </span>
                  <span className="mt-1.5 block text-lg font-medium tabular-nums text-foreground">
                    {fmt(tier.miles)} <span className="text-xs text-muted-foreground">miles</span>
                  </span>
                  <span
                    className={cn(
                      "mt-0.5 block text-xs",
                      reaches ? "text-gold" : "text-muted-foreground",
                    )}
                  >
                    {reaches
                      ? tier.monthsToGoal !== null
                        ? `Reaches your goal in month ${tier.monthsToGoal}`
                        : "Reaches your goal"
                      : `${fmt(targetMiles - tier.miles)} short of your goal`}
                    {" · "}
                    {tier.fees === 0 ? "₹0 card fees" : `${inr(tier.fees)} card fees`}
                  </span>
                </button>
              );
            })}
          </div>
          {note && (
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-foreground/85">{note}</p>
          )}
          {!note && comparisonNotes && (
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted-foreground">
              {comparisonNotes}
            </p>
          )}
        </section>
      )}

      {selected.detail ? (
        <PlanSteps
          tier={selected}
          programName={programName}
          chartMilesPerSeat={chartMilesPerSeat}
          bufferMiles={bufferMiles}
          targetMiles={targetMiles}
          risks={risks}
          nameOf={nameOf}
          partnerNameOf={partnerNameOf}
        />
      ) : (
        <CompactTierPanel tier={selected} nameOf={nameOf} />
      )}

      {selected.detail && (
        <>
          <EarnChart
            ledger={selected.detail.ledger}
            goalMonth={selected.monthsToGoal}
            horizonMonths={horizonMonths}
          />
          <WhyThisRoute
            tier={selected}
            recommended={recommended}
            targetMiles={targetMiles}
            horizonMonths={horizonMonths}
            reasoning={selected.isRecommended ? reasoning : null}
            nameOf={nameOf}
          />
        </>
      )}
    </div>
  );
}

/** Saved goals persist alternatives compactly (no per-category detail or
 * ledger) — show what we stored and say so, instead of an empty page. */
function CompactTierPanel({
  tier,
  nameOf,
}: {
  tier: PlanTier;
  nameOf: (id: string) => string;
}) {
  return (
    <section className="rounded-xl border border-hairline bg-background/40 p-4">
      <p className="text-sm text-foreground">
        {tier.cardsToAcquire.length > 0 ? (
          <>
            This route adds{" "}
            <span className="font-medium">
              {tier.cardsToAcquire.map(nameOf).join(" + ")}
            </span>{" "}
            and projects {fmt(tier.miles)} miles
            {tier.monthsToGoal !== null ? ` by month ${tier.monthsToGoal}` : ""}, for{" "}
            {tier.fees === 0 ? "no new card fees" : `${inr(tier.fees)} in card fees`}.
          </>
        ) : (
          <>
            With your current cards this route projects {fmt(tier.miles)} miles
            {tier.monthsToGoal !== null ? ` by month ${tier.monthsToGoal}` : ""}.
          </>
        )}
      </p>
      <p className="mt-2 text-xs text-muted-foreground">
        The full month-by-month breakdown was stored for the recommended route —
        re-run this goal from the simulator to explore this option in detail.
      </p>
    </section>
  );
}

// ── 3. The plan, as numbered steps (the "directions" metaphor) ─────────────

function PlanSteps({
  tier,
  programName,
  chartMilesPerSeat,
  bufferMiles,
  targetMiles,
  risks,
  nameOf,
  partnerNameOf,
}: {
  tier: PlanTier;
  programName: string;
  chartMilesPerSeat?: number | null;
  bufferMiles?: number | null;
  targetMiles: number;
  risks: string[];
  nameOf: (id: string) => string;
  partnerNameOf: (id: string) => string;
}) {
  const detail = tier.detail!;
  const steps: { title: string; body: React.ReactNode }[] = [];

  if (tier.cardsToAcquire.length > 0) {
    steps.push({
      title: "Get the new card",
      body: (
        <div className="space-y-2">
          <ul className="flex flex-wrap gap-2">
            {tier.cardsToAcquire.map((id) => (
              <li
                key={id}
                className="flex items-center gap-1.5 rounded-full border border-gold/40 bg-gold/10 px-3.5 py-1.5 text-xs font-medium text-gold"
              >
                <Plus className="size-3.5" /> {nameOf(id)}
              </li>
            ))}
          </ul>
          <p className="text-xs text-muted-foreground">
            Apply now — this plan starts counting its earning (and any welcome
            bonus) from the month it&apos;s in your wallet.
          </p>
        </div>
      ),
    });
  }

  steps.push({
    title: "Route your monthly spend",
    body: (
      <SpendStep
        details={detail.allocationDetails}
        fallbackAllocation={detail.fallbackAllocation}
        milestones={detail.milestones}
        programName={programName}
        transferStepNumber={steps.length + 2}
        nameOf={nameOf}
      />
    ),
  });

  if (detail.transferPlan.length > 0) {
    steps.push({
      title: `Transfer points to ${programName}`,
      body: (
        <div className="space-y-2">
          <ul className="space-y-2">
            {detail.transferPlan.map((step, i) => (
              <li
                key={`${step.fromCardId}-${step.plannedMonth}-${i}`}
                className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg border border-hairline bg-background/40 px-3 py-2.5 text-sm"
              >
                <span className="rounded-md bg-gold/15 px-2 py-0.5 text-xs font-medium tabular-nums text-gold">
                  Month {step.plannedMonth}
                </span>
                <span className="min-w-0 text-foreground">
                  {nameOf(step.fromCardId)}
                  <ArrowRight className="mx-1.5 inline size-3.5 text-gold" />
                  {partnerNameOf(step.toPartnerId)}
                </span>
                <span className="ml-auto shrink-0 tabular-nums text-muted-foreground">
                  {fmt(step.points)} points
                </span>
              </li>
            ))}
          </ul>
          <p className="text-xs text-muted-foreground">
            Transfers aren&apos;t instant — partners take days to land the miles. The
            months above already account for each partner&apos;s processing time.
            {tier.transferFees > 0 && (
              <>
                {" "}
                The bank charges a small program fee for these transfers (
                {inr(tier.transferFees)}
                {" across this plan), billed at transfer time — it's not part "}
                of the card fees shown above.
              </>
            )}
          </p>
        </div>
      ),
    });
  }

  steps.push({
    title: "Book your award seat",
    body: (
      <div className="space-y-2 text-sm text-foreground/90">
        <p>
          {chartMilesPerSeat
            ? `A saver award on this route costs ${fmt(chartMilesPerSeat)} ${programName} miles per seat. `
            : ""}
          Book once your {programName} balance reaches {fmt(targetMiles)} miles
          {bufferMiles
            ? ` — the plan also works toward a ${fmt(bufferMiles)}-mile cushion on top, in case rates move`
            : ""}
          .
        </p>
        {risks.length > 0 && (
          <ul className="space-y-1.5 text-xs text-muted-foreground">
            {risks.map((r) => (
              <li key={r} className="flex items-start gap-2">
                <Info className="mt-0.5 size-3.5 shrink-0" />
                <span>{r}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    ),
  });

  return (
    <section aria-label="Your plan, step by step">
      <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
        The plan, step by step
      </p>
      <ol className="mt-3 space-y-0">
        {steps.map((step, i) => (
          <li key={step.title} className="relative flex gap-4 pb-6 last:pb-0">
            {/* connector line */}
            {i < steps.length - 1 && (
              <span
                aria-hidden="true"
                className="absolute left-[15px] top-8 h-[calc(100%-2rem)] w-px bg-hairline"
              />
            )}
            <span className="z-10 grid size-8 shrink-0 place-items-center rounded-full border border-gold/40 bg-background text-sm font-medium tabular-nums text-gold">
              {i + 1}
            </span>
            <div className="min-w-0 flex-1 pt-1">
              <h5 className="text-sm font-medium text-foreground">{step.title}</h5>
              <div className="mt-2">{step.body}</div>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

/** One row's runner-up comparison, in plain language — the deterministic
 * answer to "why is my other card ignored here?". Pure comparison of two
 * engine numbers (effective miles/₹100), no reward math. */
function runnerUpSentence(r: AllocationDetail, nameOf: (id: string) => string): string | null {
  if (!r.runner_up_card_id || r.runner_up_miles_per_100inr == null) return null;
  const chosen = Number(r.effective_miles_per_100inr);
  const other = Number(r.runner_up_miles_per_100inr);
  const otherName = nameOf(r.runner_up_card_id);
  if (other < chosen) {
    return `Best card for this — ${otherName} would net ${other} miles/₹100 here vs ${chosen} on this card.`;
  }
  if (other === chosen) {
    return `Ties with ${otherName} (${other} miles/₹100) — either card works for this category.`;
  }
  // Don't invent a specific cause (caps? milestones? route shape?) — the row
  // doesn't carry attribution, so name the trade-off without asserting why.
  return `${otherName} rates higher per ₹100 here (${other} vs ${chosen} miles/₹100) — a trade-off this route accepts; caps, milestone bonuses and the route's own goal all shape the split.`;
}

const DEFAULT_RATE_NOTE = "earns at the card's default rate";

/** Step "route your spend": per-card groups that tell the full earn story —
 * the card's reward system (currency + transfer ratio), each category's rate
 * chain (points rate → effective miles/₹100), a worked monthly example, how
 * to get an accelerated rate (the catalog's rule label, e.g. a portal), and
 * the runner-up comparison. Card-wide notes (caps, transfer fees) are hoisted
 * to one line per card instead of repeating on every row. */
function SpendStep({
  details,
  fallbackAllocation,
  milestones,
  programName,
  transferStepNumber,
  nameOf,
}: {
  details: AllocationDetail[];
  fallbackAllocation?: Record<string, string>;
  milestones: { id: string; cardId: string; expectedMonth: number; bonusPoints: number }[];
  programName: string;
  transferStepNumber: number;
  nameOf: (id: string) => string;
}) {
  if (details.length === 0) {
    const entries = Object.entries(fallbackAllocation ?? {});
    if (entries.length === 0) return null;
    return (
      <ul className="space-y-2">
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
    );
  }

  // Group rows by card so "everything on one card" reads as deliberate.
  const byCard = new Map<string, AllocationDetail[]>();
  for (const d of details) {
    const list = byCard.get(d.card_id) ?? [];
    list.push(d);
    byCard.set(d.card_id, list);
  }

  // A card's honest monthly points: exact cross-category sum floored ONCE —
  // matching the engine's one-floor-per-card-month rule, never the sum of the
  // per-row floored values (which can undershoot when categories share a card).
  const cardMonthlyPoints = (rows: AllocationDetail[]): number =>
    Math.floor(
      rows.reduce((s, r) => s + (r.monthly_spend_inr * Number(r.earn_rate)) / 100, 0),
    );

  return (
    <div className="space-y-3">
      <p className="text-xs text-muted-foreground">
        Each card earns its own points on these categories — step{" "}
        {transferStepNumber} turns them into {programName} miles.
      </p>
      {[...byCard.entries()].map(([cardId, rows]) => {
        // Card-level facts are identical on every row of the card — hoist
        // them so they read once, not per category.
        const story = rows.find((r) => r.currency_name || r.transfer_ratio_from);
        const shared = (rows[0]?.notes ?? []).filter(
          (note) => rows.length > 1 && rows.every((r) => r.notes.includes(note)),
        );
        const allDefaultRate =
          rows.length > 1 && rows.every((r) => r.notes.some((n) => n.startsWith(DEFAULT_RATE_NOTE)));
        return (
          <div
            key={cardId}
            className="overflow-hidden rounded-xl border border-hairline bg-background/40"
          >
            <div className="border-b border-hairline/70 px-3.5 py-2.5">
              <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                <span className="flex min-w-0 items-center gap-2 text-sm font-medium text-foreground">
                  <CreditCard className="size-4 shrink-0 text-gold" />
                  <span className="min-w-0 wrap-break-word">{nameOf(cardId)}</span>
                </span>
                <span className="whitespace-nowrap text-xs tabular-nums text-muted-foreground">
                  ~{fmt(cardMonthlyPoints(rows))} pts/mo
                </span>
              </div>
              {story && (
                <p className="mt-1 text-xs text-muted-foreground">
                  {story.currency_name ? `Earns ${story.currency_name}` : "Earns points"}
                  {story.transfer_ratio_from != null && story.transfer_ratio_to != null && (
                    <>
                      {" · "}transfers to {programName} at{" "}
                      <span className="tabular-nums text-foreground/80">
                        {story.transfer_ratio_from}:{story.transfer_ratio_to}
                      </span>
                    </>
                  )}
                </p>
              )}
            </div>
            <ul className="divide-y divide-hairline/50">
              {rows.map((r) => {
                const comparison = runnerUpSentence(r, nameOf);
                const rowNotes = r.notes.filter(
                  (note) =>
                    !shared.includes(note) &&
                    !(allDefaultRate && note.startsWith(DEFAULT_RATE_NOTE)),
                );
                return (
                  <li key={r.category_slug} className="px-3.5 py-2.5 text-sm">
                    {/* Wraps on narrow screens — the category + ₹ amount is the
                        primary info and must never truncate away. */}
                    <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                      <span className="min-w-0 text-foreground">
                        {categoryLabel(r.category_slug)}
                        <span className="ml-2 whitespace-nowrap text-xs text-muted-foreground">
                          {inr(r.monthly_spend_inr)}/mo
                        </span>
                      </span>
                      <span className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5 text-xs tabular-nums">
                        <span className="whitespace-nowrap text-gold">
                          {Number(r.earn_rate)} pts per ₹100
                        </span>
                        <span className="whitespace-nowrap text-foreground">
                          → {Number(r.effective_miles_per_100inr)} miles/₹100
                        </span>
                      </span>
                    </div>
                    {/* The worked example: spend → points → program miles. */}
                    <p className="mt-1 text-xs tabular-nums text-muted-foreground">
                      {inr(r.monthly_spend_inr)} × {Number(r.earn_rate)}/₹100 ={" "}
                      {fmt(r.monthly_points)} pts
                      {r.monthly_miles != null && r.monthly_miles > 0 && (
                        <> → ~{fmt(r.monthly_miles)} {programName} miles a month</>
                      )}
                    </p>
                    {r.category_label && (
                      <p className="mt-1 text-xs leading-relaxed text-gold/90">
                        To get this rate: {r.category_label}
                      </p>
                    )}
                    {comparison && (
                      <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                        {comparison}
                      </p>
                    )}
                    {rowNotes.length > 0 && (
                      <ul className="mt-1 space-y-0.5 text-xs leading-relaxed text-muted-foreground/80">
                        {rowNotes.map((note, i) => (
                          <li key={i}>{note}</li>
                        ))}
                      </ul>
                    )}
                  </li>
                );
              })}
            </ul>
            {(shared.length > 0 || allDefaultRate) && (
              <div className="border-t border-hairline/70 px-3.5 py-2">
                <ul className="space-y-0.5 text-xs leading-relaxed text-muted-foreground/80">
                  {allDefaultRate && (
                    <li>
                      These categories all earn the card&apos;s flat default rate —
                      no accelerated category applies.
                    </li>
                  )}
                  {shared
                    .filter((note) => !note.startsWith(DEFAULT_RATE_NOTE))
                    .map((note, i) => (
                      <li key={i}>{note}</li>
                    ))}
                </ul>
              </div>
            )}
          </div>
        );
      })}
      {milestones.length > 0 && (
        <div className="rounded-xl border border-hairline bg-background/40 px-3.5 py-3">
          <p className="flex items-center gap-1.5 text-xs font-medium text-foreground">
            <Award className="size-3.5 text-gold" /> Bonuses this plan collects along the way
          </p>
          <ul className="mt-2 space-y-1.5">
            {milestones.map((m) => (
              <li
                key={m.id}
                className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm"
              >
                <span className="rounded-md bg-gold/15 px-2 py-0.5 text-xs font-medium tabular-nums text-gold">
                  Month {m.expectedMonth}
                </span>
                <span className="min-w-0 text-foreground">{nameOf(m.cardId)}</span>
                <span className="ml-auto shrink-0 tabular-nums text-muted-foreground">
                  +{fmt(m.bonusPoints)} points
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ── 4. Chart: earning over the window, with the goal month marked ──────────

export function EarnChart({
  ledger,
  goalMonth,
  horizonMonths,
}: {
  ledger: { month: number; pointsEarned: number }[];
  goalMonth: number | null;
  horizonMonths: number | null;
}) {
  const gradientId = useId();
  const [hover, setHover] = useState<number | null>(null);

  if (ledger.length < 2) return null;

  // Cumulative points earned month by month — the earn delta summed, NOT the
  // balance (which dips on transfer), so the curve is honestly monotonic.
  const series: number[] = [];
  let running = 0;
  for (const entry of ledger) {
    running += entry.pointsEarned;
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

  const goalInRange = goalMonth !== null && goalMonth >= 0 && goalMonth < n;
  const subtitle =
    goalMonth !== null && horizonMonths !== null
      ? `Goal reached in month ${goalMonth} of your ${horizonMonths}-month window.`
      : horizonMonths !== null
        ? `Your ${horizonMonths}-month window.`
        : null;

  return (
    <section>
      <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
        Points earned, month by month
      </p>
      {subtitle && <p className="mt-1 text-xs text-muted-foreground/80">{subtitle}</p>}
      <div className="relative mt-3">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          preserveAspectRatio="none"
          className="h-24 w-full"
          role="img"
          aria-label={`Reward points accumulating over ${n} months, reaching ${max.toLocaleString()} points${
            goalMonth !== null ? `; goal reached in month ${goalMonth}` : ""
          }`}
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
          {goalInRange && (
            <line
              x1={x(goalMonth)}
              y1="0"
              x2={x(goalMonth)}
              y2={H}
              stroke="var(--color-gold)"
              strokeOpacity="0.5"
              strokeWidth="1"
              strokeDasharray="2 2"
              vectorEffect="non-scaling-stroke"
            />
          )}
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
        {goalInRange && (
          <span
            className="pointer-events-none absolute -top-1 flex -translate-x-1/2 items-center gap-1 rounded-full border border-gold/30 bg-background px-2 py-0.5 text-[10px] text-gold"
            // Clamp so the centered pill never spills past the card edges
            // when the goal month sits at either end of the window.
            style={{
              left: `clamp(2.25rem, ${(goalMonth / (n - 1)) * 100}%, calc(100% - 2.25rem))`,
            }}
          >
            <Plane className="size-3" /> goal
          </span>
        )}
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

// ── 5. Why this route — reasons in English, raw scores demoted ─────────────

const SCORE_EXPLAINERS: { key: keyof ScoreBreakdown; label: string; explainer: string }[] = [
  {
    key: "goal_achievement",
    label: "Goal achievement",
    explainer: "How early the route finishes inside your window — higher means more slack.",
  },
  {
    key: "efficiency",
    label: "Efficiency",
    explainer:
      "Miles earned relative to the other routes above — 0 means the fewest of this set, not zero miles.",
  },
  {
    key: "cost",
    label: "Cost",
    explainer: "Fees, inverted — 100 is the cheapest route of this set.",
  },
  {
    key: "simplicity",
    label: "Simplicity",
    explainer: "Fewer cards to juggle and fewer new applications score higher.",
  },
  {
    key: "portfolio_utilization",
    label: "Uses your cards",
    explainer: "The share of your spend that stays on cards you already own.",
  },
  {
    key: "risk",
    label: "Risk buffer",
    explainer:
      "Starts at 100 and is docked when a transfer runs close to a partner's annual cap or a slow partner could delay arrival — higher is safer.",
  },
];

export function WhyThisRoute({
  tier,
  recommended,
  targetMiles,
  horizonMonths,
  reasoning,
  nameOf,
}: {
  tier: PlanTier;
  recommended: PlanTier;
  targetMiles: number;
  horizonMonths: number | null;
  reasoning?: string | null;
  nameOf: (id: string) => string;
}) {
  const detail = tier.detail;
  const reaches = tier.miles >= targetMiles;
  const isRec = tier.strategyId === recommended.strategyId;

  // Plain-language reasons, each derived from an engine artifact.
  const reasons: string[] = [];
  if (reaches && tier.monthsToGoal !== null && horizonMonths !== null) {
    const slack = horizonMonths - tier.monthsToGoal;
    reasons.push(
      slack > 0
        ? `Reaches your ${fmt(targetMiles)}-mile target in month ${tier.monthsToGoal} — ${slack === 1 ? "a month" : `${slack} months`} inside your window`
        : `Reaches your ${fmt(targetMiles)}-mile target right at your deadline`,
    );
  } else if (!reaches) {
    reasons.push(`Falls ${fmt(targetMiles - tier.miles)} miles short of your target`);
  }
  reasons.push(
    tier.fees === 0
      ? "Costs nothing extra — ₹0 in new card fees"
      : `Costs ${inr(tier.fees)} in card fees — the price of the extra earning`,
  );
  reasons.push(
    tier.cardsToAcquire.length === 0
      ? "No new cards to apply for — works with what's in your wallet"
      : `Requires adding ${tier.cardsToAcquire.map(nameOf).join(" and ")}`,
  );

  return (
    <section>
      <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
        {isRec ? "Why this is the recommended route" : "What this route means"}
      </p>
      <ul className="mt-3 space-y-2">
        {reasons.map((r) => (
          <li key={r} className="flex items-start gap-2.5 text-sm text-foreground/90">
            <BadgeCheck className="mt-0.5 size-4 shrink-0 text-gold" />
            <span>{r}</span>
          </li>
        ))}
      </ul>
      {reasoning && (
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted-foreground">
          {reasoning}
        </p>
      )}
      {detail?.scoreBreakdown && (
        <ScoreDisclosure breakdown={detail.scoreBreakdown} score={detail.score} />
      )}
    </section>
  );
}

/** The raw six-dimension scoring, demoted to an opt-in disclosure with the
 * semantics spelled out — sub-scores are comparisons within this candidate
 * set, not grades, and shown as such. */
function ScoreDisclosure({
  breakdown,
  score,
}: {
  breakdown: ScoreBreakdown;
  score: string | null;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-4">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
      >
        <ChevronDown className={cn("size-3.5 transition-transform", open && "rotate-180")} />
        How OptiMiles scored this route{score ? ` (${Math.round(Number(score))}/100 weighted)` : ""}
      </button>
      {open && (
        <div className="mt-3 rounded-xl border border-hairline bg-background/40 p-4">
          <p className="text-xs leading-relaxed text-muted-foreground">
            Routes are compared with each other on six dimensions, then combined
            with versioned weights. These are comparisons within your options —
            not grades — so a low bar doesn&apos;t mean a bad plan.
          </p>
          <ul className="mt-3 space-y-3">
            {SCORE_EXPLAINERS.map(({ key, label, explainer }) => {
              const value = Math.max(0, Math.min(100, Number(breakdown[key])));
              return (
                <li key={key}>
                  <div className="flex items-center gap-3">
                    <span className="w-32 shrink-0 text-sm text-muted-foreground">{label}</span>
                    <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-input/40">
                      <span
                        className="block h-full rounded-full bg-gold"
                        style={{ width: `${value}%` }}
                      />
                    </span>
                    <span className="w-8 shrink-0 text-right text-xs tabular-nums text-foreground">
                      {Math.round(value)}
                    </span>
                  </div>
                  <p className="mt-1 pl-0 text-xs leading-relaxed text-muted-foreground/80 sm:pl-[8.75rem]">
                    {explainer}
                  </p>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}

// ── 6. Next steps + fine print ──────────────────────────────────────────────

export function NextSteps({
  items,
}: {
  items: { priority: number; action: string; impact: string | null }[];
}) {
  if (items.length === 0) return null;
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
              <BadgeCheck className="size-3" />
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

export function FinePrint({
  snapshotVersion,
  engineVersion,
}: {
  snapshotVersion?: string | null;
  engineVersion?: string | null;
}) {
  return (
    <div className="text-xs text-muted-foreground/70">
      <p>
        Every number above comes from verified award charts, transfer ratios,
        caps and milestone rules — computed deterministically, never estimated
        by AI.
      </p>
      {(snapshotVersion || engineVersion) && (
        <p className="mt-1 text-[10px] text-muted-foreground/50">
          {[
            snapshotVersion ? `Catalog ${snapshotVersion.slice(0, 8)}` : null,
            engineVersion ? `engine ${engineVersion}` : null,
          ]
            .filter(Boolean)
            .join(" · ")}
        </p>
      )}
    </div>
  );
}
