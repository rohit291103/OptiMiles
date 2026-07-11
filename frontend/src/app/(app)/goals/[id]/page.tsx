"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Calendar, Target, TrendingUp } from "lucide-react";

import { getAccessToken } from "@/lib/supabase";
import { fetchSavedGoal, type SavedGoalDetail } from "@/lib/api";
import { SavedStrategyView } from "@/components/app/saved-strategy";
import { PlaneLoader } from "@/components/ui/plane-loader";

/**
 * A saved goal opened into its full stored strategy. Every number is the
 * persisted engine artifact from save time — the header names the catalog
 * snapshot it was computed against, honoring the "explainable, never a black
 * box" promise for past runs too.
 */

type LoadState =
  | { phase: "loading" }
  | { phase: "ready"; detail: SavedGoalDetail }
  | { phase: "error"; message: string };

export default function GoalDetailPage() {
  const params = useParams<{ id: string }>();
  const goalId = params.id;
  const [state, setState] = useState<LoadState>({ phase: "loading" });

  useEffect(() => {
    let active = true;
    (async () => {
      const token = await getAccessToken();
      if (!token) return; // AppShell is already redirecting to /login.
      try {
        const detail = await fetchSavedGoal(goalId, token);
        if (active) setState({ phase: "ready", detail });
      } catch (e) {
        if (active)
          setState({
            phase: "error",
            message: e instanceof Error ? e.message : "Couldn't load this goal.",
          });
      }
    })();
    return () => {
      active = false;
    };
  }, [goalId]);

  return (
    <div className="space-y-6">
      <Link
        href="/goals"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="size-4" /> Back to dashboard
      </Link>

      {state.phase === "loading" && <StrategySkeleton />}

      {state.phase === "error" && (
        <div className="rounded-xl border border-destructive/40 bg-destructive/5 p-4">
          <p className="text-sm text-destructive" role="alert">
            {state.message}
          </p>
        </div>
      )}

      {state.phase === "ready" && <GoalDetail detail={state.detail} />}
    </div>
  );
}

/** On-brand loading placeholder that mirrors the strategy layout: title,
 * three stat tiles, chart block, and a couple of routing rows — so the page
 * keeps its shape while the persisted artifacts load, instead of a bare line. */
function StrategySkeleton() {
  return (
    <div className="space-y-8">
      <PlaneLoader stages={["Loading your strategy…", "Rebuilding your plan…"]} />
      <div className="animate-pulse space-y-8" aria-hidden="true">
        <div className="space-y-3">
          <div className="h-8 w-2/3 rounded-lg bg-card/70" />
          <div className="h-4 w-1/2 rounded bg-card/50" />
        </div>
        <div className="grid gap-4 sm:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-24 rounded-xl border border-hairline bg-card/40" />
          ))}
        </div>
        <div className="space-y-3">
          <div className="h-3 w-40 rounded bg-card/50" />
          <div className="h-28 rounded-xl border border-hairline bg-card/30" />
        </div>
        <div className="space-y-2">
          <div className="h-3 w-32 rounded bg-card/50" />
          <div className="h-11 rounded-lg border border-hairline bg-card/30" />
          <div className="h-11 rounded-lg border border-hairline bg-card/30" />
        </div>
      </div>
    </div>
  );
}

function GoalDetail({ detail }: { detail: SavedGoalDetail }) {
  const strategy = detail.strategy;
  const confidence =
    detail.confidence_score !== null
      ? Math.round(detail.confidence_score * 100)
      : null;

  return (
    <div className="space-y-8">
      <header>
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="font-heading text-2xl text-foreground sm:text-3xl">
            {detail.goal_name}
          </h2>
          <span className="rounded-full border border-hairline px-2.5 py-0.5 text-[11px] uppercase tracking-wide text-muted-foreground">
            {detail.status}
          </span>
        </div>
        <p className="mt-2 text-sm text-muted-foreground">
          {[
            detail.origin_city && detail.destination_city
              ? `${detail.origin_city} → ${detail.destination_city}`
              : detail.destination_city,
            detail.cabin_class ? cabinLabel(detail.cabin_class) : null,
            detail.num_passengers
              ? `${detail.num_passengers} ${detail.num_passengers === 1 ? "passenger" : "passengers"}`
              : null,
            detail.target_date ? `by ${formatDate(detail.target_date)}` : null,
          ]
            .filter(Boolean)
            .join(" · ")}
        </p>
      </header>

      <section className="grid gap-4 sm:grid-cols-3">
        <StatTile
          icon={<Target className="size-4" />}
          label="Miles required"
          value={detail.target_miles.toLocaleString("en-IN")}
        />
        <StatTile
          icon={<Calendar className="size-4" />}
          label="Months to goal"
          value={
            strategy?.months_to_goal !== null && strategy?.months_to_goal !== undefined
              ? String(strategy.months_to_goal)
              : "—"
          }
        />
        <StatTile
          icon={<TrendingUp className="size-4" />}
          label="Confidence"
          value={confidence !== null ? `${confidence} / 100` : "—"}
        />
      </section>

      {!strategy && (
        <div className="rounded-xl border border-hairline bg-card/50 p-4">
          <p className="text-sm text-foreground/85">
            This goal wasn&apos;t achievable as stated when it was saved — the
            notes below show what would make it work.
          </p>
        </div>
      )}

      <SavedStrategyView detail={detail} />

      <p className="border-t border-hairline pt-4 text-xs text-muted-foreground/70">
        Saved {formatDate(detail.saved_at)}
        {detail.catalog_snapshot_version
          ? ` · computed against catalog snapshot ${detail.catalog_snapshot_version.slice(0, 12)}`
          : ""}
        {detail.engine_version ? ` · engine ${detail.engine_version}` : ""}
      </p>
    </div>
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
