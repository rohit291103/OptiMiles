"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  Calendar,
  Download,
  Eye,
  MoreVertical,
  Plane,
  Plus,
  Target,
  Trash2,
  TrendingUp,
} from "lucide-react";

import { getAccessToken } from "@/lib/supabase";
import {
  deleteSavedGoal,
  fetchSavedGoal,
  fetchSavedGoals,
  type SavedGoal,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { PlaneLoader } from "@/components/ui/plane-loader";

/**
 * The dashboard home — the signed-in landing page. Reads only persisted
 * engine artifacts (never recomputes): stat tiles across all saved goals up
 * top, a focus strip for the newest goal beneath them, and a grid of every
 * goal, each opening into its stored strategy at /goals/[id] and carrying a
 * per-goal action menu (view / download / delete).
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

  if (state.phase === "loading") return <DashboardSkeleton />;

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

  const focus = goals[0];
  const removeGoal = (goalId: string) =>
    setState((s) =>
      s.phase === "ready"
        ? { phase: "ready", goals: s.goals.filter((g) => g.goal_id !== goalId) }
        : s,
    );

  return (
    <div className="space-y-8">
      <StatTiles goals={goals} />
      <FocusGoal goal={focus} />
      <section>
        <h2 className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
          All goals
        </h2>
        <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {goals.map((goal) => (
            <GoalCard key={goal.goal_id} goal={goal} onDeleted={removeGoal} />
          ))}
        </div>
      </section>
    </div>
  );
}

// ── Loading skeleton ───────────────────────────────────────────────────────

/** Mirrors the dashboard layout (stat row, focus hero, goal grid) so the page
 * holds its shape while goals load — on-brand, not a bare loading line. */
function DashboardSkeleton() {
  return (
    <div className="space-y-8">
      <PlaneLoader stages={LOADING_STAGES} />
      <div className="animate-pulse space-y-8" aria-hidden="true">
        <div className="grid gap-4 sm:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-24 rounded-xl border border-hairline bg-card/40" />
          ))}
        </div>
        <div className="h-52 rounded-2xl border border-gold/20 bg-card/40" />
        <div className="space-y-3">
          <div className="h-3 w-24 rounded bg-card/50" />
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-40 rounded-xl border border-hairline bg-card/30" />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// Short, dashboard-appropriate copy (this load is a fast DB read, not a full
// pipeline run — keep it to two calm lines rather than the pipeline narration).
const LOADING_STAGES = ["Loading your goals…", "Fetching your saved strategies…"];

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
        unit={goals.length === 1 ? "goal" : "goals"}
      />
      <StatTile
        icon={<TrendingUp className="size-4" />}
        label="Total miles targeted"
        value={totalMiles.toLocaleString("en-IN")}
        unit="miles"
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
  unit,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  unit?: string;
}) {
  return (
    <div className="rounded-xl border border-hairline bg-card/50 p-5">
      <p className="flex items-center gap-1.5 text-xs uppercase tracking-[0.12em] text-muted-foreground">
        <span className="text-gold">{icon}</span>
        {label}
      </p>
      <p className="mt-2 font-heading text-2xl tabular-nums text-foreground sm:text-3xl">
        {value}
        {unit && (
          <span className="ml-1.5 align-baseline font-sans text-sm text-muted-foreground">
            {unit}
          </span>
        )}
      </p>
    </div>
  );
}

// ── Focus strip: the newest goal, hero-sized ───────────────────────────────

function FocusGoal({ goal }: { goal: SavedGoal }) {
  const monthsLeft = monthsUntil(goal.target_date);
  const confidence =
    goal.confidence_score !== null ? Math.round(goal.confidence_score * 100) : null;
  // The focus slot shows the NEWEST goal, whatever its status — only claim
  // "Active" (and pulse) when the persisted status actually says so.
  const isActive = goal.status === "active";

  return (
    <section className="relative overflow-hidden rounded-2xl border border-gold/45 bg-gradient-to-br from-gold/15 via-card/60 to-card/40 p-6 shadow-[0_0_50px_-18px] shadow-gold/40 sm:p-8">
      <p className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.12em] text-gold">
        {isActive && (
          <span className="relative flex size-2" aria-hidden="true">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-gold/60 motion-reduce:animate-none" />
            <span className="relative inline-flex size-2 rounded-full bg-gold" />
          </span>
        )}
        <Plane className="size-3.5" />
        {isActive ? "Active goal" : `${titleCase(goal.status)} goal`}
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

// ── Goal grid cards ────────────────────────────────────────────────────────

function GoalCard({
  goal,
  onDeleted,
}: {
  goal: SavedGoal;
  onDeleted: (goalId: string) => void;
}) {
  const confidence =
    goal.confidence_score !== null ? Math.round(goal.confidence_score * 100) : null;

  return (
    <div className="group relative rounded-xl border border-hairline bg-card/50 p-5 transition-colors hover:border-gold/40">
      <div className="flex items-start justify-between gap-2">
        {/* Stretched link: the whole card navigates; the menu sits above it. */}
        <h3 className="min-w-0 flex-1 truncate font-medium text-foreground">
          <Link
            href={`/goals/${goal.goal_id}`}
            className="after:absolute after:inset-0 after:rounded-xl"
          >
            {goal.goal_name}
          </Link>
        </h3>
        <span
          className={`shrink-0 rounded-full border px-2 py-0.5 text-[11px] uppercase tracking-wide ${
            goal.status === "active"
              ? "border-gold/40 bg-gold/10 font-medium text-gold"
              : "border-hairline text-muted-foreground"
          }`}
        >
          {goal.status}
        </span>
        <GoalMenu goal={goal} onDeleted={onDeleted} />
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
    </div>
  );
}

// ── Per-goal action menu (view / download / delete) ────────────────────────

function GoalMenu({
  goal,
  onDeleted,
}: {
  goal: SavedGoal;
  onDeleted: (goalId: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [menuError, setMenuError] = useState<string | null>(null);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);

  // Close the popover on outside click / Escape. Listeners only while open.
  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: PointerEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  const download = async () => {
    setDownloading(true);
    setMenuError(null);
    try {
      const token = await getAccessToken();
      if (!token) throw new Error("Your session expired — please log in again.");
      const detail = await fetchSavedGoal(goal.goal_id, token);
      const blob = new Blob([JSON.stringify(detail, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `optimiles-${slugify(goal.goal_name)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      setOpen(false);
    } catch (e) {
      setMenuError(e instanceof Error ? e.message : "Download failed.");
    } finally {
      setDownloading(false);
    }
  };

  const confirmDelete = async () => {
    setDeleting(true);
    setDeleteError(null);
    try {
      const token = await getAccessToken();
      if (!token) throw new Error("Your session expired — please log in again.");
      await deleteSavedGoal(goal.goal_id, token);
      // Success: the card unmounts as the parent drops it from state.
      onDeleted(goal.goal_id);
    } catch (e) {
      setDeleteError(e instanceof Error ? e.message : "Couldn't delete this goal.");
      setDeleting(false); // keep the dialog open so the error is visible
    }
  };

  return (
    <div ref={rootRef} className="relative z-10 -mr-1.5 -mt-1 shrink-0">
      <button
        type="button"
        aria-label={`Actions for ${goal.goal_name}`}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => {
          setOpen((o) => !o);
          setMenuError(null);
        }}
        className="grid size-8 place-items-center rounded-lg text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
      >
        <MoreVertical className="size-4" />
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 top-9 z-20 w-52 overflow-hidden rounded-xl border border-hairline bg-card p-1 shadow-xl shadow-black/40"
        >
          <Link
            href={`/goals/${goal.goal_id}`}
            role="menuitem"
            className="flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-foreground transition-colors hover:bg-secondary"
          >
            <Eye className="size-4 text-muted-foreground" /> View strategy
          </Link>
          <button
            type="button"
            role="menuitem"
            disabled={downloading}
            onClick={download}
            className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-foreground transition-colors hover:bg-secondary disabled:opacity-50"
          >
            <Download className="size-4 text-muted-foreground" />
            {downloading ? "Preparing…" : "Download strategy"}
          </button>
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              setOpen(false);
              setDeleteError(null);
              setConfirmingDelete(true);
            }}
            className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-destructive transition-colors hover:bg-destructive/10"
          >
            <Trash2 className="size-4" /> Delete goal
          </button>
          {menuError && (
            <p className="px-3 py-2 text-xs text-destructive" role="alert">
              {menuError}
            </p>
          )}
        </div>
      )}

      <ConfirmDialog
        open={confirmingDelete}
        destructive
        title="Delete this goal?"
        description={
          <>
            <span className="font-medium text-foreground">{goal.goal_name}</span>{" "}
            and its saved strategy will be permanently removed. This can&apos;t be
            undone.
          </>
        }
        confirmLabel="Delete goal"
        busyLabel="Deleting…"
        busy={deleting}
        errorMessage={deleteError}
        onConfirm={confirmDelete}
        onCancel={() => {
          if (!deleting) {
            setConfirmingDelete(false);
            setDeleteError(null);
          }
        }}
      />
    </div>
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

function titleCase(s: string): string {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

function slugify(name: string): string {
  return (
    name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "goal"
  );
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
