"use client";

import type { FinalRecommendation, RankedStrategy } from "@/lib/api";
import {
  AdjustmentMenu,
  FinePrint,
  NextSteps,
  StrategyPlanTabs,
  VerdictHero,
  type PlanTier,
} from "@/components/strategy-story";

/**
 * The live simulator's result — the full strategy narrative for a fresh
 * engine run. Every tier in the response carries its own allocation detail,
 * transfer plan and ledger, so switching tabs swaps the entire plan.
 * Every value is a deterministic engine artifact; card ids resolve through
 * the catalog map the simulator already fetched.
 */

function toTier(r: RankedStrategy, recommendedId: string): PlanTier {
  return {
    strategyId: r.strategy.strategy_id,
    miles: r.simulation.miles_at_target_date,
    // "Fees" to the user = what the new card costs; bank transfer micro-fees
    // are shown once in the transfer step, not folded into the headline.
    fees: r.simulation.card_fees_inr,
    transferFees: r.simulation.transfer_fees_inr,
    monthsToGoal: r.simulation.months_to_goal,
    cardsToAcquire: r.strategy.cards_to_acquire,
    isRecommended: r.strategy.strategy_id === recommendedId,
    headline: r.headline_differentiator,
    detail: {
      allocationDetails: r.allocation_details,
      fallbackAllocation: r.strategy.spend_allocation,
      transferPlan: r.strategy.transfer_plan.map((t) => ({
        fromCardId: t.from_card_id,
        toPartnerId: t.to_partner_id,
        points: t.points,
        plannedMonth: t.planned_month,
      })),
      milestones: r.strategy.expected_milestones.map((m) => ({
        id: m.milestone_id,
        cardId: m.card_id,
        expectedMonth: m.expected_month,
        bonusPoints: m.bonus_points,
      })),
      ledger: r.simulation.ledger.map((e) => ({
        month: e.month,
        pointsEarned: e.points_earned_this_month,
      })),
      scoreBreakdown: r.score_breakdown,
      score: r.score,
    },
  };
}

export function StrategyDetail({
  rec,
  cardNames,
  horizonMonths,
  preferNoNewCards = false,
}: {
  rec: FinalRecommendation;
  cardNames: Map<string, string>;
  horizonMonths: number | null;
  preferNoNewCards?: boolean;
}) {
  const recommended = rec.recommended;
  if (!recommended) return null;

  const nameOf = (id: string) => cardNames.get(id) ?? "Selected card";
  const programName = rec.requirement.target_program_name;
  // MVP transfer plans move points into the goal's program; the live response
  // has no partner-name map, so the requirement's program name is the honest
  // label for any transfer destination.
  const partnerNameOf = () => programName;

  const recommendedId = recommended.strategy.strategy_id;
  const tiers = [recommended, ...rec.alternatives].map((r) => toTier(r, recommendedId));

  return (
    <div className="mt-6 space-y-6">
      <VerdictHero
        feasible={rec.verdict.feasible}
        tight={rec.verdict.tight}
        targetMiles={rec.requirement.miles_required_total}
        projectedMiles={recommended.simulation.miles_at_target_date}
        goalMonth={recommended.simulation.months_to_goal}
        horizonMonths={horizonMonths}
        newFees={recommended.simulation.card_fees_inr}
        cardsToAcquireNames={recommended.strategy.cards_to_acquire.map(nameOf)}
        programName={programName}
        narrationSummary={rec.narration?.summary}
        bestEffort={!rec.verdict.feasible}
        hasAdjustments={rec.verdict.adjustment_options.length > 0}
      />
      {/* Unreachable-as-stated goals ship a best-effort plan AND the computed
          changes that would actually close the gap. */}
      {!rec.verdict.feasible && (
        <AdjustmentMenu options={rec.verdict.adjustment_options} />
      )}
      <StrategyPlanTabs
        tiers={tiers}
        targetMiles={rec.requirement.miles_required_total}
        horizonMonths={horizonMonths}
        programName={programName}
        chartMilesPerSeat={rec.requirement.chart_miles_per_passenger}
        bufferMiles={rec.requirement.buffer_miles}
        risks={rec.risks_and_limitations}
        reasoning={rec.narration?.reasoning}
        comparisonNotes={rec.narration?.comparison_notes}
        nameOf={nameOf}
        partnerNameOf={partnerNameOf}
        preferNoNewCards={preferNoNewCards}
      />
      <NextSteps items={rec.narration?.action_items ?? []} />
      <FinePrint
        snapshotVersion={rec.catalog_snapshot_version}
        engineVersion={rec.engine_version}
      />
    </div>
  );
}
