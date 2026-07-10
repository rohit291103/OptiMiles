"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, Plane, Sparkles, TrendingUp } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { CountUp } from "@/components/ui/count-up";
import {
  ApiError,
  fetchCards,
  simulate,
  simulateAndSave,
  type CardSummary,
  type FinalRecommendation,
  type SimulateRequest,
  type SimulateResponse,
} from "@/lib/api";
import { StrategyDetail } from "@/components/strategy-detail";
import { getAccessToken } from "@/lib/supabase";
import { useAuth } from "@/lib/use-auth";

// Backend-supported destinations (goal_resolution.CITY_TO_REGION). Europe /
// North America are charted in business only, so the UI nudges toward it.
const DESTINATIONS = ["Singapore", "London", "New York"];
const ORIGINS = ["Hyderabad", "Mumbai", "Delhi", "Bangalore", "Chennai", "Pune"];

const CABINS = [
  { label: "Economy", value: "economy" },
  { label: "Business", value: "business" },
  { label: "First", value: "first" },
] as const;

// The public simulator collects a single monthly-spend figure, but the engine
// earns per category (accelerated categories are the whole point). A signed-in
// user edits their real profile; here we spread the figure over a representative
// premium-traveler mix so the result reflects categorized earning, not the low
// uncategorized "default" rate. Fractions sum to 1.
const SPEND_MIX: { category_slug: string; fraction: number }[] = [
  { category_slug: "travel", fraction: 0.3 },
  { category_slug: "dining", fraction: 0.2 },
  { category_slug: "online", fraction: 0.2 },
  { category_slug: "groceries", fraction: 0.15 },
  { category_slug: "utilities", fraction: 0.15 },
];

function splitSpend(monthly: number): {
  category_slug: string;
  monthly_spend_inr: number;
}[] {
  return SPEND_MIX.map(({ category_slug, fraction }) => ({
    category_slug,
    monthly_spend_inr: Math.max(Math.round(monthly * fraction), 1),
  }));
}

export function GoalSimulator() {
  const [origin, setOrigin] = useState(ORIGINS[0]);
  const [destination, setDestination] = useState(DESTINATIONS[0]);
  const [cabin, setCabin] = useState<(typeof CABINS)[number]["value"]>("business");
  const [monthlySpend, setMonthlySpend] = useState("100000");
  const [timeline, setTimeline] = useState("8");
  const [selectedCardIds, setSelectedCardIds] = useState<string[]>([]);

  const [cards, setCards] = useState<CardSummary[]>([]);
  const [response, setResponse] = useState<SimulateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // The exact request behind the current result, so "Save" persists the same
  // inputs the user is looking at. Save state is separate from the run state.
  const [lastRequest, setLastRequest] = useState<SimulateRequest | null>(null);
  const [saveState, setSaveState] = useState<
    "idle" | "saving" | "saved" | "error" | "session_expired"
  >("idle");
  const { user, loading: authLoading } = useAuth();

  const cabinLabel =
    CABINS.find((c) => c.value === cabin)?.label.toLowerCase() ?? "business";
  const cardNames = new Map(cards.map((c) => [c.id, c.card_name]));
  const pickerCards = cards.filter((c) => c.acquirable);

  // Load the real card catalog for the wallet picker (falls back to no picker
  // if the backend is unreachable — the sim still runs with an empty wallet).
  useEffect(() => {
    let active = true;
    fetchCards()
      .then((fetched) => {
        if (!active) return;
        setCards(fetched);
        // Pre-select the two flagship cards if present.
        const defaults = fetched
          .filter((c) => c.acquirable && /Infinia|Atlas/.test(c.card_name))
          .map((c) => c.id)
          .slice(0, 2);
        setSelectedCardIds(defaults);
      })
      .catch(() => {
        if (active) setCards([]);
      });
    return () => {
      active = false;
    };
  }, []);

  function toggleCard(id: string) {
    setSelectedCardIds((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id],
    );
  }

  function buildRequest(): SimulateRequest {
    return {
      intent: {
        origin_city: origin,
        destination_city: destination,
        cabin_class: cabin,
        timeline_months: Math.max(Number(timeline) || 1, 1),
        num_passengers: 1,
        confidence: 1,
      },
      wallet: selectedCardIds.map((id) => ({
        card_id: id,
        current_points_balance: 0,
      })),
      spend_profile: splitSpend(Math.max(Number(monthlySpend) || 1, 1)),
    };
  }

  async function handleCalculate() {
    setLoading(true);
    setError(null);
    setResponse(null);
    setSaveState("idle");
    const request = buildRequest();
    try {
      const result = await simulate(request);
      setResponse(result);
      setLastRequest(request);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Something went wrong building your strategy.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    if (!lastRequest) return;
    setSaveState("saving");
    try {
      const token = await getAccessToken();
      if (!token) {
        // No token ⇒ the session lapsed since load; retrying won't help.
        setSaveState("session_expired");
        return;
      }
      // Re-runs the pipeline server-side and persists it under the user. The
      // result is deterministic, so it matches what's already on screen.
      const result = await simulateAndSave(lastRequest, token);
      // Trust the server's own report: persistence is best-effort, so a 200
      // doesn't guarantee the row landed. Only claim "Saved" when it did.
      const saved =
        result.kind === "recommendation" && result.persisted === true;
      setSaveState(saved ? "saved" : "error");
    } catch {
      setSaveState("error");
    }
  }

  return (
    <div className="overflow-hidden rounded-[2rem] border border-white/10 bg-card/60 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] backdrop-blur-sm">
      <div className="flex items-center gap-3 border-b border-hairline px-6 py-5 sm:px-8">
        <span className="grid size-9 shrink-0 place-items-center rounded-xl border border-gold/30 bg-gold/10 text-gold">
          <Sparkles className="size-4" />
        </span>
        <h3 className="font-heading text-xl text-foreground sm:text-2xl">
          I want to fly{" "}
          <span className="italic text-gold">{cabinLabel} class</span> to{" "}
          <span className="italic text-gold">{destination}</span>
        </h3>
      </div>

      <div className="p-6 sm:p-8">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="origin" className="text-muted-foreground">
              Flying from
            </Label>
            <select
              id="origin"
              value={origin}
              onChange={(e) => setOrigin(e.target.value)}
              className="flex h-10 w-full rounded-lg border border-input bg-input/30 px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            >
              {ORIGINS.map((c) => (
                <option key={c} value={c} className="bg-card">
                  {c}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="destination" className="text-muted-foreground">
              Destination
            </Label>
            <select
              id="destination"
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
              className="flex h-10 w-full rounded-lg border border-input bg-input/30 px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            >
              {DESTINATIONS.map((d) => (
                <option key={d} value={d} className="bg-card">
                  {d}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="spend" className="text-muted-foreground">
              Monthly spend (₹)
            </Label>
            <Input
              id="spend"
              type="number"
              value={monthlySpend}
              onChange={(e) => setMonthlySpend(e.target.value)}
              className="h-10 bg-input/30"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="timeline" className="text-muted-foreground">
              Timeline (months)
            </Label>
            <Input
              id="timeline"
              type="number"
              min={1}
              value={timeline}
              onChange={(e) => setTimeline(e.target.value)}
              className="h-10 bg-input/30"
            />
          </div>
        </div>

        <div className="mt-4 space-y-2">
          <Label className="text-muted-foreground">Cabin class</Label>
          <div className="inline-flex w-full rounded-lg border border-hairline bg-input/20 p-1 sm:w-auto">
            {CABINS.map((c) => (
              <button
                key={c.value}
                type="button"
                onClick={() => setCabin(c.value)}
                aria-pressed={cabin === c.value}
                className={`flex-1 rounded-md px-4 py-1.5 text-sm font-medium transition-colors sm:flex-none ${
                  cabin === c.value
                    ? "bg-gold text-gold-foreground"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {c.label}
              </button>
            ))}
          </div>
        </div>

        {pickerCards.length > 0 && (
          <div className="mt-4 space-y-2">
            <Label className="text-muted-foreground">Your credit cards</Label>
            <div className="flex flex-wrap gap-2">
              {pickerCards.map((card) => {
                const selected = selectedCardIds.includes(card.id);
                return (
                  <button
                    key={card.id}
                    type="button"
                    onClick={() => toggleCard(card.id)}
                    aria-pressed={selected}
                    className={`rounded-full border px-3.5 py-1.5 text-xs font-medium transition-colors ${
                      selected
                        ? "border-gold/40 bg-gold/15 text-gold"
                        : "border-hairline text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {card.card_name}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        <Button
          onClick={handleCalculate}
          size="lg"
          disabled={loading}
          className="mt-6 w-full bg-gold text-gold-foreground hover:bg-gold/90 disabled:opacity-60 sm:w-auto"
        >
          {loading ? "Building your strategy…" : "Build my card strategy"}
          {!loading && <ArrowRight />}
        </Button>

        {error && (
          <p className="mt-4 text-sm text-destructive" role="alert">
            {error}
          </p>
        )}

        <div aria-live="polite">
          {response && (
            <SimulatorResult
              response={response}
              destination={destination}
              cardNames={cardNames}
            />
          )}
        </div>

        {/* Save — only for a real recommendation the user can persist. */}
        {/* Wait for auth to resolve so a returning user doesn't flash the
            logged-out "Log in to save" prompt before their session loads. */}
        {response?.kind === "recommendation" && lastRequest && !authLoading && (
          <SaveGoal
            isLoggedIn={Boolean(user)}
            state={saveState}
            onSave={handleSave}
          />
        )}
      </div>
    </div>
  );
}

function SaveGoal({
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
        {state === "saving"
          ? "Saving…"
          : state === "saved"
            ? "Saved ✓"
            : "Save this goal"}
      </Button>
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

function SimulatorResult({
  response,
  destination,
  cardNames,
}: {
  response: SimulateResponse;
  destination: string;
  cardNames: Map<string, string>;
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

  return <RecommendationView rec={response.recommendation} cardNames={cardNames} />;
}

function RecommendationView({
  rec,
  cardNames,
}: {
  rec: FinalRecommendation;
  cardNames: Map<string, string>;
}) {
  const { requirement, verdict, recommended, narration } = rec;
  const milesNeeded = requirement.miles_required_total;
  const bestCase = verdict.best_case_miles;
  const monthsToGoal = recommended?.simulation.months_to_goal ?? null;
  const progress = Math.min(
    100,
    Math.round((bestCase / Math.max(milesNeeded, 1)) * 100),
  );

  return (
    <div className="mt-8 space-y-6 border-t border-hairline pt-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <Stat
          icon={<Plane className="size-4" />}
          label="Miles required"
          value={<CountUp value={milesNeeded} />}
        />
        <Stat
          icon={<TrendingUp className="size-4" />}
          label="Best-case miles"
          value={<CountUp value={bestCase} />}
        />
        <Stat
          label="Time to goal"
          value={monthsToGoal !== null ? `${monthsToGoal} months` : "—"}
        />
      </div>

      <div>
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>Projected progress</span>
          <span className="font-medium text-foreground">{progress}%</span>
        </div>
        <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-input/40">
          <div
            className="h-full rounded-full bg-gold transition-all duration-700"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 rounded-xl border border-hairline bg-background/40 p-4">
        <Badge className="bg-gold text-gold-foreground hover:bg-gold/90">
          {verdict.feasible
            ? verdict.tight
              ? "Achievable (tight)"
              : "Achievable"
            : "Not as stated"}
        </Badge>
        {recommended && (
          <span className="text-sm text-foreground">
            Best route: {recommended.headline_differentiator}
          </span>
        )}
      </div>

      {narration?.summary && (
        <p className="text-sm text-foreground">{narration.summary}</p>
      )}

      {/* The explainable detail — only when there's a recommended strategy. */}
      {recommended && <StrategyDetail rec={rec} cardNames={cardNames} />}

      {/* Infeasible → the adjustment menu is the answer, not a strategy list. */}
      {!verdict.feasible && verdict.adjustment_options.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
            To make it work
          </p>
          <ul className="space-y-2">
            {verdict.adjustment_options.map((opt) => (
              <li
                key={opt.kind + opt.description}
                className="rounded-lg border border-hairline bg-background/40 px-4 py-2.5 text-sm text-foreground"
              >
                {opt.description}
              </li>
            ))}
          </ul>
        </div>
      )}

      <p className="text-xs text-muted-foreground/70">
        Computed from verified award charts, live transfer ratios, caps and
        milestones — snapshot {rec.catalog_snapshot_version.slice(0, 8)}.
      </p>
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

function Stat({
  label,
  value,
  icon,
}: {
  label: string;
  value: React.ReactNode;
  icon?: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-hairline bg-background/40 p-4">
      <p className="flex items-center gap-1.5 text-xs uppercase tracking-[0.12em] text-muted-foreground">
        {icon}
        {label}
      </p>
      <p className="mt-1.5 font-heading text-xl text-foreground">{value}</p>
    </div>
  );
}
