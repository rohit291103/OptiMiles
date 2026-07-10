"use client";

import { GoalSimulator } from "@/components/goal-simulator";

/**
 * Goal creation inside the app — the same live simulator the homepage embeds,
 * so signed-in users never bounce back to the marketing page. Saving shows a
 * link straight back to the dashboard.
 */
export default function NewGoalPage() {
  return (
    <div className="space-y-6">
      <header>
        <h2 className="font-heading text-2xl text-foreground">Plan a new goal</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Pick the trip and your cards — the engine builds the strategy,
          explainably, from verified award charts and transfer ratios.
        </p>
      </header>
      <GoalSimulator />
    </div>
  );
}
