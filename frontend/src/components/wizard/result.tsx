"use client";

import Link from "next/link";

import { Button } from "@/components/ui/button";
import type { FinalRecommendation, SimulateResponse } from "@/lib/api";
import { StrategyDetail } from "@/components/strategy-detail";
import { AdjustmentMenu, FinePrint, VerdictHero } from "@/components/strategy-story";

/**
 * The wizard's final-step result rendering: the response union → the full
 * strategy narrative, an honest early-exit note, or the adjustment-menu-only
 * infeasible view. Extracted from the retired one-shot simulator (slice 10)
 * — the wizard is now the only goal-entry surface.
 */

export function SimulatorResult({
  response,
  destination,
  cardNames,
  horizonMonths,
  preferNoNewCards,
}: {
  response: SimulateResponse;
  destination: string;
  cardNames: Map<string, string>;
  horizonMonths: number | null;
  preferNoNewCards: boolean;
}) {
  if (response.kind === "clarification") {
    return (
      <Note title="A few more details">
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-foreground">
          {response.clarification.questions.map((q) => (
            <li key={q}>{q}</li>
          ))}
        </ul>
      </Note>
    );
  }

  if (response.kind === "unsupported_route") {
    return (
      <Note title="Route not covered yet">
        <p className="mt-2 text-sm text-foreground">
          {destination} in this cabin isn&apos;t in our verified award charts
          yet. Supported today:{" "}
          {response.unsupported_route.supported_routes.join(", ")}.
        </p>
      </Note>
    );
  }

  if (response.kind === "scope_refusal") {
    return (
      <Note title="Out of scope">
        <p className="mt-2 text-sm text-foreground">
          {response.message ?? "This goal is outside what we can help with today."}
        </p>
      </Note>
    );
  }

  return (
    <RecommendationView
      rec={response.recommendation}
      cardNames={cardNames}
      horizonMonths={horizonMonths}
      preferNoNewCards={preferNoNewCards}
    />
  );
}

function RecommendationView({
  rec,
  cardNames,
  horizonMonths,
  preferNoNewCards,
}: {
  rec: FinalRecommendation;
  cardNames: Map<string, string>;
  horizonMonths: number | null;
  preferNoNewCards: boolean;
}) {
  const { requirement, verdict, recommended, narration } = rec;

  // A recommendation → the full narrative (verdict, route tabs, plan steps,
  // chart, why). No plan at all → an honest verdict plus the adjustment menu.
  if (recommended) {
    return (
      <div className="mt-8 border-t border-hairline pt-6">
        {/* Keyed on the preference so toggling it re-applies the default
            route selection instead of keeping stale tab state. */}
        <StrategyDetail
          key={`plan-${preferNoNewCards}`}
          rec={rec}
          cardNames={cardNames}
          horizonMonths={horizonMonths}
          preferNoNewCards={preferNoNewCards}
        />
      </div>
    );
  }

  return (
    <div className="mt-8 space-y-6 border-t border-hairline pt-6">
      <VerdictHero
        feasible={false}
        tight={verdict.tight}
        targetMiles={requirement.miles_required_total}
        projectedMiles={verdict.best_case_miles}
        goalMonth={null}
        horizonMonths={horizonMonths}
        newFees={0}
        cardsToAcquireNames={[]}
        programName={requirement.target_program_name}
        narrationSummary={narration?.summary}
      />
      <AdjustmentMenu options={verdict.adjustment_options} />
      <FinePrint snapshotVersion={rec.catalog_snapshot_version} engineVersion={rec.engine_version} />
    </div>
  );
}

function Note({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mt-8 rounded-xl border border-hairline bg-background/40 p-5">
      <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
        {title}
      </p>
      {children}
    </div>
  );
}

export function SaveGoal({
  isLoggedIn,
  state,
  onSave,
}: {
  isLoggedIn: boolean;
  state: "idle" | "saving" | "saved" | "error" | "session_expired";
  onSave: () => void;
}) {
  if (!isLoggedIn) {
    return (
      <p className="mt-6 border-t border-hairline pt-6 text-sm text-muted-foreground">
        <a href="/login" className="text-gold hover:underline">
          Log in
        </a>{" "}
        to save this goal and track your progress.
      </p>
    );
  }

  return (
    <div className="mt-6 flex flex-wrap items-center gap-3 border-t border-hairline pt-6">
      <Button
        onClick={onSave}
        disabled={state === "saving" || state === "saved"}
        variant="outline"
        className="border-gold/40 text-gold hover:bg-gold/10 disabled:opacity-60"
      >
        {state === "saving" ? (
          <>
            <span
              aria-hidden="true"
              className="size-4 animate-spin rounded-full border-2 border-gold/30 border-t-gold motion-reduce:animate-none"
            />
            Saving…
          </>
        ) : state === "saved" ? (
          "Saved ✓"
        ) : (
          "Save this goal"
        )}
      </Button>
      {state === "saving" && (
        <span className="text-sm text-muted-foreground" role="status">
          Recomputing and saving your strategy — this can take up to a minute.
          Keep this page open until you see &ldquo;Saved ✓&rdquo;.
        </span>
      )}
      {state === "saved" && (
        <span className="text-sm text-muted-foreground" role="status">
          Saved to your account.{" "}
          <Link href="/goals" className="font-medium text-gold hover:underline">
            View it on your dashboard →
          </Link>
        </span>
      )}
      {state === "error" && (
        <span className="text-sm text-destructive" role="alert">
          Couldn&apos;t save — please try again.
        </span>
      )}
      {state === "session_expired" && (
        <span className="text-sm text-destructive" role="alert">
          Your session expired —{" "}
          <a href="/login" className="underline">
            log in again
          </a>{" "}
          to save.
        </span>
      )}
    </div>
  );
}
