"use client";

import { GoalWizard } from "@/components/goal-wizard";

/**
 * Goal creation inside the app — the guided wizard (decision log 2026-07-13):
 * goal → cards → total spend → education → opt-in split → strategy, one
 * conversational-scroll page. The same wizard the public homepage embeds
 * (decision 1: one goal-entry experience everywhere). Saving shows a link
 * straight back to the dashboard.
 */
export default function NewGoalPage() {
  return (
    <div className="space-y-6">
      <header>
        <h2 className="font-heading text-3xl text-foreground">Plan a new goal</h2>
        <p className="mt-1.5 max-w-2xl text-base text-muted-foreground">
          Say the trip, pick the cards you hold, give us a spending ballpark —
          the engine builds your route to the award seat from verified charts
          and transfer ratios, and shows its work.
        </p>
      </header>
      <GoalWizard />
    </div>
  );
}
