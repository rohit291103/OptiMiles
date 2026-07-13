"use client";

import type { SavedGoalDetail } from "@/lib/api";
import {
  AdjustmentMenu,
  NextSteps,
  StrategyPlanTabs,
  VerdictHero,
  type PlanTier,
} from "@/components/strategy-story";

/**
 * Renders a *persisted* recommendation in the same narrative shape as the
 * live simulator: verdict → route tabs → plan steps → chart → why. Nothing
 * here is recomputed; every number is the stored engine artifact from save
 * time. Only the recommended route was persisted in full — alternative tiers
 * are compact summaries, and the tab panel says so instead of pretending.
 * Card/partner ids resolve through the response's name maps and fall back to
 * a generic label if a catalog id has since been retired.
 */
export function SavedStrategyView({ detail }: { detail: SavedGoalDetail }) {
  const strategy = detail.strategy;
  const cardName = (id: string) => detail.card_names[id] ?? "Card no longer listed";
  const partnerName = (id: string) =>
    detail.partner_names[id] ?? "Transfer partner";

  // The persisted requirement doesn't include the program name; the transfer
  // plan's destination partner is the honest stand-in ("KrisFlyer").
  const programName =
    strategy && strategy.transfer_plan.length > 0
      ? partnerName(strategy.transfer_plan[0].to_partner_id)
      : "the airline program";

  // Compact persisted tiers; the recommended one gets the fully-stored plan.
  const tiers: PlanTier[] = detail.strategy_options.map((o) => ({
    strategyId: o.strategy_id,
    miles: o.miles_at_target_date,
    // Card fees when the save carries the split; older saves fall back to the
    // stored total (which folded transfer fees in).
    fees: o.card_fees_inr ?? o.total_fees_inr,
    transferFees: o.transfer_fees_inr ?? 0,
    monthsToGoal: o.months_to_goal,
    cardsToAcquire: o.cards_to_acquire,
    isRecommended: o.is_recommended,
    headline: o.headline_differentiator,
    detail:
      o.is_recommended && strategy
        ? {
            allocationDetails: strategy.allocation_details,
            fallbackAllocation: strategy.spend_allocation,
            transferPlan: strategy.transfer_plan.map((t) => ({
              fromCardId: t.from_card_id,
              toPartnerId: t.to_partner_id,
              points: t.points,
              plannedMonth: t.planned_month,
            })),
            milestones: strategy.milestones.map((m) => ({
              id: m.milestone_id,
              cardId: m.card_id,
              expectedMonth: m.expected_month,
              bonusPoints: m.bonus_points,
            })),
            ledger: strategy.ledger.map((e) => ({
              month: e.month,
              pointsEarned: e.points_earned_this_month,
            })),
            scoreBreakdown: strategy.score_breakdown,
            score: strategy.optimization_score,
          }
        : null,
  }));

  // Older saves have no strategy_options — synthesize the one stored tier so
  // the plan still renders.
  if (tiers.length === 0 && strategy) {
    tiers.push({
      strategyId: "saved",
      miles: strategy.ledger.at(-1)?.cumulative_target_miles ?? 0,
      fees: 0,
      transferFees: 0,
      monthsToGoal: strategy.months_to_goal,
      cardsToAcquire: strategy.cards_to_acquire,
      isRecommended: true,
      headline: strategy.headline_differentiator ?? "",
      detail: {
        allocationDetails: strategy.allocation_details,
        fallbackAllocation: strategy.spend_allocation,
        transferPlan: strategy.transfer_plan.map((t) => ({
          fromCardId: t.from_card_id,
          toPartnerId: t.to_partner_id,
          points: t.points,
          plannedMonth: t.planned_month,
        })),
        milestones: strategy.milestones.map((m) => ({
          id: m.milestone_id,
          cardId: m.card_id,
          expectedMonth: m.expected_month,
          bonusPoints: m.bonus_points,
        })),
        ledger: strategy.ledger.map((e) => ({
          month: e.month,
          pointsEarned: e.points_earned_this_month,
        })),
        scoreBreakdown: strategy.score_breakdown,
        score: strategy.optimization_score,
      },
    });
  }

  const recommendedTier = tiers.find((t) => t.isRecommended) ?? tiers[0] ?? null;
  // The horizon isn't persisted; the ledger runs the full window, so its
  // length is the stored horizon in months.
  const horizonMonths =
    strategy && strategy.ledger.length > 1 ? strategy.ledger.length : null;
  // Infeasible goals now persist a best-effort plan, so strategy presence no
  // longer implies feasibility — the persisted recommendation_type is the
  // truth ("goal_feasibility" = infeasible). Older rows without it fall back
  // to the old inference.
  const feasible = detail.recommendation_type
    ? detail.recommendation_type !== "goal_feasibility"
    : Boolean(strategy);

  return (
    <div className="space-y-6">
      <VerdictHero
        feasible={feasible}
        bestEffort={!feasible && Boolean(strategy)}
        hasAdjustments={(detail.adjustment_options ?? []).length > 0}
        tight={false}
        targetMiles={detail.target_miles}
        projectedMiles={recommendedTier?.miles ?? 0}
        goalMonth={strategy?.months_to_goal ?? null}
        horizonMonths={horizonMonths}
        newFees={recommendedTier?.fees ?? 0}
        cardsToAcquireNames={(strategy?.cards_to_acquire ?? []).map(cardName)}
        programName={programName}
        narrationSummary={detail.summary}
      />

      {/* Best-effort infeasible saves persist the Stage-6 adjustment menu —
          the hero's "changes that would close the gap" promise. Older saves
          have none; the summary/reasoning prose then carries the story. */}
      {!feasible && (
        <AdjustmentMenu options={detail.adjustment_options ?? []} />
      )}

      {tiers.length > 0 && (
        <StrategyPlanTabs
          tiers={tiers}
          targetMiles={detail.target_miles}
          horizonMonths={horizonMonths}
          programName={programName}
          risks={[]}
          reasoning={detail.reasoning}
          nameOf={cardName}
          partnerNameOf={partnerName}
        />
      )}

      <NextSteps items={detail.action_items} />
    </div>
  );
}
