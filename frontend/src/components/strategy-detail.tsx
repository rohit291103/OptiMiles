"use client";

import { useState } from "react";

import type { FinalRecommendation, RankedStrategy } from "@/lib/api";
import {
  AdjustmentMenu,
  ExtraCardAsk,
  FinePrint,
  NextSteps,
  StrategyPlanTabs,
  VerdictHero,
  WalletShortfallHero,
  type PlanTier,
} from "@/components/strategy-story";

/**
 * The live simulator's result — the full strategy narrative for a fresh
 * engine run. Every tier in the response carries its own allocation detail,
 * transfer plan and ledger, so switching tabs swaps the entire plan.
 * Every value is a deterministic engine artifact; card ids resolve through
 * the catalog map the simulator already fetched.
 *
 * End-of-flow verdict shapes (guided flow, decision 8):
 * - wallet clears the goal → confident hero, alternatives as quiet upgrades;
 * - wallet falls short but an added card clears it (the engine labels the
 *   pair via `acquisition_role`) → honest wallet-shortfall hero + the
 *   wallet's own best plan, with the acquisition routes revealed only after
 *   the explicit "want strategies with additional cards?" ask;
 * - nothing clears it → best-effort hero + the adjustment menu (unchanged).
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
    acquisitionRole: r.acquisition_role ?? null,
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
  // The extra-card ask is opt-in (decision 8) — routes with added cards stay
  // hidden until the user clicks. State lives here so a new run resets it
  // (the component remounts with the new response).
  const [revealExtra, setRevealExtra] = useState(false);

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

  // Guided end-of-flow shape: labeled acquisition routes exist AND there is a
  // wallet-only route to weigh them against. (An empty wallet has labels but
  // nothing to compare — the pair renders directly, no ask.)
  const labeledTiers = tiers.filter((t) => t.acquisitionRole);
  const walletTier = tiers.find((t) => t.cardsToAcquire.length === 0);
  const guidedAsk = labeledTiers.length > 0 && walletTier !== undefined;

  // Decision 8's feasible path: current cards clear it → the acquisition
  // alternatives read as optional upgrades, not competing routes.
  const upgradesFraming =
    !guidedAsk &&
    recommended.strategy.cards_to_acquire.length === 0 &&
    tiers.some((t) => t.cardsToAcquire.length > 0);

  if (guidedAsk && walletTier) {
    return (
      <div className="mt-6 space-y-6">
        <WalletShortfallHero
          walletMiles={walletTier.miles}
          targetMiles={rec.requirement.miles_required_total}
          programName={programName}
        />
        {!revealExtra ? (
          <>
            {/* Distinct keys force a remount across the reveal — the tab
                selection state must recompute for the new tier list, or the
                reveal appears to change nothing (stale selectedId). */}
            <StrategyPlanTabs
              key="wallet-only"
              tiers={[walletTier]}
              targetMiles={rec.requirement.miles_required_total}
              horizonMonths={horizonMonths}
              programName={programName}
              chartMilesPerSeat={rec.requirement.chart_miles_per_passenger}
              bufferMiles={rec.requirement.buffer_miles}
              risks={rec.risks_and_limitations}
              reasoning={null}
              comparisonNotes={null}
              nameOf={nameOf}
              partnerNameOf={partnerNameOf}
            />
            <ExtraCardAsk
              count={labeledTiers.length}
              onReveal={() => setRevealExtra(true)}
            />
          </>
        ) : (
          <>
            <StrategyPlanTabs
              key="revealed"
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
              heading="Routes with an added card — compared with staying put"
            />
            <NextSteps items={rec.narration?.action_items ?? []} />
          </>
        )}
        <FinePrint
          snapshotVersion={rec.catalog_snapshot_version}
          engineVersion={rec.engine_version}
        />
      </div>
    );
  }

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
        heading={
          upgradesFraming
            ? "Optional upgrades — add a card to go further"
            : undefined
        }
      />
      <NextSteps items={rec.narration?.action_items ?? []} />
      <FinePrint
        snapshotVersion={rec.catalog_snapshot_version}
        engineVersion={rec.engine_version}
      />
    </div>
  );
}
