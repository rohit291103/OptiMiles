"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, Calendar, Plane, Plus, Target, TrendingUp } from "lucide-react";

import { getAccessToken } from "@/lib/supabase";
import { fetchSavedGoals, type SavedGoal } from "@/lib/api";
import { Button } from "@/components/ui/button";

/**
 * The dashboard home — the signed-in landing page. Reads only persisted
 * engine artifacts (never recomputes): a focus strip for the newest goal,
 * honest stat tiles across all saved goals, and a grid of goal cards that
 * each open into their stored strategy at /goals/[id].
 */

type LoadState =
  | { phase: "loading" }
  | { phase: "ready"; goals: SavedGoal[] }
  | { phase: "error"; message: string };

export default function DashboardPage() {
  const [state, setState] = useState<LoadState>({ phase: "loading" });

  useEffect(() => {
    let active = true;
    (async () => {
      const token = await getAccessToken();
      if (!token) return; // AppShell is already redirecting to /login.
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
  }, []);

  if (state.phase === "loading") {
    return (
      <p className="text-sm text-muted-foreground" role="status">
        Loading your goals…
      </p>
    );
  }

  if (state.phase === "error") {
    return (
      <div className="rounded-xl border border-destructive/40 bg-destructive/5 p-4">
        <p className="text-sm text-destructive" role="alert">
          {state.message}
        </p>
      </div>
    );
  }

  const goals = state.goals;
  if (goals.length === 0) return <EmptyDashboard />;

  const [focus, ...rest] = goals;

  return (
    <div className="space-y-8">
      <FocusGoal goal={focus} />
      <StatTiles goals={goals} />
      {rest.length > 0 && (
        <section>
          <h2 className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
            All goals
          </h2>
          <div className="mt-3 grid gap-4 sm:grid-cols-2">
            {rest.map((goal) => (
              <GoalCard key={goal.goal_id} goal={goal} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

// ── Focus strip: the newest goal, hero-sized ───────────────────────────────

function FocusGoal({ goal }: { goal: SavedGoal }) {
  const monthsLeft = monthsUntil(goal.target_date);
  const confidence =
    goal.confidence_score !== null ? Math.round(goal.confidence_score * 100) : null;

  return (
    <section className="relative overflow-hidden rounded-2xl border border-gold/20 bg-gradient-to-br from-gold/10 via-card/60 to-card/40 p-6 sm:p-8">
      <p className="flex items-center gap-2 text-xs uppercase tracking-[0.12em] text-gold">
        <Plane className="size-3.5" /> Your current goal
      </p>
      <h2 className="mt-3 font-heading text-2xl text-foreground sm:text-3xl">
        {goal.goal_name}
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">
        {[
          goal.destination_city,
          goal.cabin_class ? cabinLabel(goal.cabin_class) : null,
          `${goal.target_miles.toLocaleString("en-IN")} miles needed`,
        ]
          .filter(Boolean)
          .join(" · ")}
      </p>

      <div className="mt-5 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
        {monthsLeft !== null && (
          <span className="flex items-center gap-1.5 text-foreground">
            <Calendar className="size-4 text-gold" />
            {monthsLeft <= 0 ? "Target date reached" : `${monthsLeft} months to target`}
          </span>
        )}
        {confidence !== null && (
          <span className="flex min-w-40 flex-1 items-center gap-2 sm:max-w-64">
            <span className="text-xs text-muted-foreground">Confidence</span>
            <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-input/40">
              <span
                className="block h-full rounded-full bg-gold"
                style={{ width: `${confidence}%` }}
              />
            </span>
            <span className="text-xs tabular-nums text-foreground">{confidence}</span>
          </span>
        )}
      </div>

      {goal.summary && (
        <p className="mt-4 max-w-2xl text-sm text-foreground/85">{goal.summary}</p>
      )}

      <div className="mt-6">
        <Button asChild className="bg-gold text-gold-foreground hover:bg-gold/90">
          <Link href={`/goals/${goal.goal_id}`}>
            View strategy <ArrowRight className="size-4" />
          </Link>
        </Button>
      </div>
    </section>
  );
}

// ── Stat tiles: honest aggregates over persisted goals ─────────────────────

function StatTiles({ goals }: { goals: SavedGoal[] }) {
  const totalMiles = goals.reduce((sum, g) => sum + g.target_miles, 0);
  const nearest = goals
    .map((g) => g.target_date)
    .filter((d): d is string => d !== null)
    .sort()[0];

  return (
    <section className="grid gap-4 sm:grid-cols-3">
      <StatTile
        icon={<Target className="size-4" />}
        label="Saved goals"
        value={String(goals.length)}
      />
      <StatTile
        icon={<TrendingUp className="size-4" />}
        label="Total miles targeted"
        value={totalMiles.toLocaleString("en-IN")}
      />
      <StatTile
        icon={<Calendar className="size-4" />}
        label="Nearest target date"
        value={nearest ? formatDate(nearest) : "—"}
      />
    </section>
  );
}

function StatTile({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-xl border border-hairline bg-card/50 p-4">
      <p className="flex items-center gap-1.5 text-xs uppercase tracking-[0.12em] text-muted-foreground">
        <span className="text-gold">{icon}</span>
        {label}
      </p>
      <p className="mt-1.5 font-heading text-xl text-foreground">{value}</p>
    </div>
  );
}

// ── Goal grid cards ────────────────────────────────────────────────────────

function GoalCard({ goal }: { goal: SavedGoal }) {
  const confidence =
    goal.confidence_score !== null ? Math.round(goal.confidence_score * 100) : null;

  return (
    <Link
      href={`/goals/${goal.goal_id}`}
      className="group rounded-xl border border-hairline bg-card/50 p-5 transition-colors hover:border-gold/40"
    >
      <div className="flex items-start justify-between gap-3">
        <h3 className="min-w-0 truncate font-medium text-foreground">{goal.goal_name}</h3>
        <span className="shrink-0 rounded-full border border-hairline px-2 py-0.5 text-[11px] uppercase tracking-wide text-muted-foreground">
          {goal.status}
        </span>
      </div>
      <p className="mt-1 text-sm text-muted-foreground">
        {[
          goal.destination_city,
          goal.cabin_class ? cabinLabel(goal.cabin_class) : null,
          `${goal.target_miles.toLocaleString("en-IN")} miles`,
        ]
          .filter(Boolean)
          .join(" · ")}
      </p>
      {goal.summary && (
        <p className="mt-3 line-clamp-2 text-sm text-foreground/80">{goal.summary}</p>
      )}
      <div className="mt-4 flex items-center justify-between">
        <p className="text-xs text-muted-foreground">
          Saved {formatDate(goal.saved_at)}
          {confidence !== null ? ` · confidence ${confidence}` : ""}
        </p>
        <span className="flex items-center gap-1 text-xs font-medium text-gold opacity-0 transition-opacity group-hover:opacity-100">
          View strategy <ArrowRight className="size-3.5" />
        </span>
      </div>
    </Link>
  );
}

// ── Empty state ────────────────────────────────────────────────────────────

function EmptyDashboard() {
  return (
    <div className="grid place-items-center rounded-2xl border border-dashed border-hairline bg-card/30 px-6 py-20 text-center">
      <div className="max-w-md">
        <span className="mx-auto grid size-12 place-items-center rounded-2xl border border-gold/30 bg-gold/10 text-gold">
          <Plane className="size-5" />
        </span>
        <h2 className="mt-5 font-heading text-2xl text-foreground">
          Where do you want to fly?
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Tell us the trip — we&apos;ll build the card strategy that gets you
          there, explainably, from your real spending.
        </p>
        <Button asChild className="mt-6 bg-gold text-gold-foreground hover:bg-gold/90">
          <Link href="/goals/new">
            <Plus className="size-4" /> Start your first goal
          </Link>
        </Button>
      </div>
    </div>
  );
}

// ── Helpers ────────────────────────────────────────────────────────────────

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
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

/** Whole months from today until the goal's target date (display only). */
function monthsUntil(iso: string | null): number | null {
  if (!iso) return null;
  const target = new Date(iso);
  if (Number.isNaN(target.getTime())) return null;
  const now = new Date();
  const months =
    (target.getFullYear() - now.getFullYear()) * 12 +
    (target.getMonth() - now.getMonth());
  return months;
}
