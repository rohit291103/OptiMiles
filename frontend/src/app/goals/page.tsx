"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowRight, Plane, Plus } from "lucide-react";

import { useAuth } from "@/lib/use-auth";
import { getAccessToken } from "@/lib/supabase";
import { fetchSavedGoals, type SavedGoal } from "@/lib/api";

/**
 * "My Goals" — the signed-in home. Lists the reward strategies the user saved,
 * newest first, each showing its destination/cabin, target miles, the one-line
 * recommendation summary, and the snapshot it was computed against. This is
 * where OAuth lands a returning user (the callback redirects here).
 *
 * Read-only for now: opening a goal into the full StrategyDetail is the next
 * slice. Every value shown is a persisted engine artifact, never recomputed.
 */

type LoadState =
  | { phase: "loading" }
  | { phase: "ready"; goals: SavedGoal[] }
  | { phase: "error"; message: string };

export default function MyGoalsPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const [state, setState] = useState<LoadState>({ phase: "loading" });

  useEffect(() => {
    if (authLoading) return;
    // Not signed in ⇒ nothing to show; send to login.
    if (!user) {
      router.replace("/login");
      return;
    }

    let active = true;
    (async () => {
      const token = await getAccessToken();
      if (!token) {
        if (active) router.replace("/login");
        return;
      }
      try {
        const goals = await fetchSavedGoals(token);
        if (active) setState({ phase: "ready", goals });
      } catch (e) {
        if (active)
          setState({
            phase: "error",
            message: e instanceof Error ? e.message : "Couldn't load your goals.",
          });
      }
    })();

    return () => {
      active = false;
    };
  }, [authLoading, user, router]);

  return (
    <main className="mx-auto w-full max-w-3xl px-6 py-16">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">Your reward strategies</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Goals you&apos;ve saved, and the plan behind each one.
        </p>
      </header>

      {(authLoading || state.phase === "loading") && (
        <p className="text-sm text-muted-foreground" role="status">
          Loading your goals…
        </p>
      )}

      {state.phase === "error" && (
        <div className="rounded-lg border border-destructive/40 bg-destructive/5 p-4">
          <p className="text-sm text-destructive" role="alert">
            {state.message}
          </p>
        </div>
      )}

      {state.phase === "ready" && (
        <div className="space-y-4">
          {state.goals.length === 0 ? (
            <EmptyState />
          ) : (
            <>
              {state.goals.map((goal) => (
                <GoalCard key={goal.goal_id} goal={goal} />
              ))}
              <NewGoalLink />
            </>
          )}
        </div>
      )}
    </main>
  );
}

function GoalCard({ goal }: { goal: SavedGoal }) {
  return (
    <article className="rounded-lg border border-border bg-card p-5">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 text-gold" aria-hidden>
          <Plane className="size-5" />
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="truncate font-medium">{goal.goal_name}</h2>
          <p className="mt-0.5 text-sm text-muted-foreground">
            {[
              goal.destination_city,
              goal.cabin_class ? cabinLabel(goal.cabin_class) : null,
              `${goal.target_miles.toLocaleString("en-IN")} miles`,
            ]
              .filter(Boolean)
              .join(" · ")}
          </p>
          {goal.summary && (
            <p className="mt-2 text-sm text-foreground/80">{goal.summary}</p>
          )}
          <p className="mt-3 text-xs text-muted-foreground">
            Saved {formatDate(goal.saved_at)}
            {goal.catalog_snapshot_version
              ? ` · snapshot ${goal.catalog_snapshot_version}`
              : ""}
          </p>
        </div>
      </div>
    </article>
  );
}

function EmptyState() {
  return (
    <div className="rounded-lg border border-dashed border-border bg-card/50 p-8 text-center">
      <p className="text-sm text-muted-foreground">
        You haven&apos;t saved any goals yet.
      </p>
      <Link
        href="/#simulator"
        className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-gold hover:underline"
      >
        Start your first goal <ArrowRight className="size-4" />
      </Link>
    </div>
  );
}

function NewGoalLink() {
  return (
    <Link
      href="/#simulator"
      className="flex items-center justify-center gap-2 rounded-lg border border-dashed border-border p-4 text-sm font-medium text-muted-foreground transition-colors hover:border-gold hover:text-gold"
    >
      <Plus className="size-4" /> Start a new goal
    </Link>
  );
}

function cabinLabel(cabin: string): string {
  const map: Record<string, string> = {
    economy: "Economy",
    premium_economy: "Premium economy",
    business: "Business",
    first: "First",
  };
  return map[cabin] ?? cabin;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}
