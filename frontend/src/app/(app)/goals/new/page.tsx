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
        <h2 className="font-heading text-3xl text-foreground">Plan a new goal</h2>
        <p className="mt-1.5 max-w-2xl text-base text-muted-foreground">
          Say the trip, tell us what you hold and spend — the engine builds
          your route to the award seat from verified charts and transfer
          ratios, and shows its work.
        </p>
      </header>
      <GoalSimulator />
    </div>
  );
}
