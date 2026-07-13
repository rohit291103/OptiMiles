"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowRight, Check, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PlaneLoader } from "@/components/ui/plane-loader";
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
import { AdjustmentMenu, FinePrint, VerdictHero } from "@/components/strategy-story";
import { getAccessToken } from "@/lib/supabase";
import { useAuth } from "@/lib/use-auth";

// Backend-supported destinations (goal_resolution.CITY_TO_REGION). Europe /
// North America are charted in business only, so the UI nudges toward it.
const DESTINATIONS = ["Singapore", "London", "New York"];
const ORIGINS = ["Hyderabad", "Mumbai", "Delhi", "Bangalore", "Chennai", "Pune"];
const PASSENGERS = [1, 2, 3, 4];

const CABINS = [
  { label: "economy", value: "economy" },
  { label: "business", value: "business" },
  { label: "first", value: "first" },
] as const;

// The spend profile is entered per category — the engine earns per category
// (accelerated categories are the whole point), so the user should see and
// control exactly what the engine sees, not a single figure secretly split.
const SPEND_CATEGORIES: { slug: string; label: string; initial: string }[] = [
  { slug: "travel", label: "Travel", initial: "30000" },
  { slug: "dining", label: "Dining", initial: "20000" },
  { slug: "online", label: "Online shopping", initial: "20000" },
  { slug: "groceries", label: "Groceries", initial: "15000" },
  { slug: "utilities", label: "Utilities", initial: "15000" },
];

export function GoalSimulator() {
  const [origin, setOrigin] = useState(ORIGINS[0]);
  const [destination, setDestination] = useState(DESTINATIONS[0]);
  const [cabin, setCabin] = useState<(typeof CABINS)[number]["value"]>("business");
  const [timeline, setTimeline] = useState("8");
  const [passengers, setPassengers] = useState(1);
  const [spend, setSpend] = useState<Record<string, string>>(
    Object.fromEntries(SPEND_CATEGORIES.map((c) => [c.slug, c.initial])),
  );
  const [openToNewCards, setOpenToNewCards] = useState(true);
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

  // The finished strategy renders far below the form — bring it into view so
  // the user isn't left staring at the button wondering whether it's done.
  const resultRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (loading || !response || !resultRef.current) return;
    const reduceMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    resultRef.current.scrollIntoView({
      behavior: reduceMotion ? "auto" : "smooth",
      block: "start",
    });
  }, [loading, response]);

  const cardNames = new Map(cards.map((c) => [c.id, c.card_name]));
  // "Cards you already hold" lists the FULL catalog — `acquirable` gates what
  // the engine may propose as a NEW card, not what a user can hold (Atlas is
  // closed to new applicants but plenty of wallets have one). Grouped by bank
  // so the picker reads like a wallet, not a flat tag dump.
  const cardsByBank: [string, CardSummary[]][] = [];
  for (const card of cards) {
    const group = cardsByBank.find(([bank]) => bank === card.bank);
    if (group) group[1].push(card);
    else cardsByBank.push([card.bank, [card]]);
  }
  const totalSpend = SPEND_CATEGORIES.reduce(
    (sum, c) => sum + Math.max(Math.round(Number(spend[c.slug]) || 0), 0),
    0,
  );

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
          .filter((c) => /Infinia|Atlas/.test(c.card_name))
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
    const spendProfile = SPEND_CATEGORIES.map((c) => ({
      category_slug: c.slug,
      monthly_spend_inr: Math.max(Math.round(Number(spend[c.slug]) || 0), 0),
    })).filter((item) => item.monthly_spend_inr > 0);
    return {
      intent: {
        origin_city: origin,
        destination_city: destination,
        cabin_class: cabin,
        timeline_months: Math.max(Number(timeline) || 1, 1),
        num_passengers: passengers,
        confidence: 1,
      },
      wallet: selectedCardIds.map((id) => ({
        card_id: id,
        current_points_balance: 0,
      })),
      // No categories entered ⇒ omit, so the engine applies its (flagged)
      // default template instead of an empty profile.
      ...(spendProfile.length > 0 ? { spend_profile: spendProfile } : {}),
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
      {/* ── The goal, as the sentence you'd say out loud ── */}
      <div className="border-b border-hairline px-6 py-6 sm:px-8">
        <p className="flex items-center gap-2 text-xs uppercase tracking-[0.12em] text-muted-foreground">
          <span className="grid size-7 shrink-0 place-items-center rounded-lg border border-gold/30 bg-gold/10 text-gold">
            <Sparkles className="size-3.5" />
          </span>
          Your goal
        </p>
        <p className="mt-4 font-heading text-2xl leading-[2.1] text-foreground sm:text-3xl sm:leading-loose">
          I want to fly{" "}
          <InlineSelect
            ariaLabel="Cabin class"
            value={cabin}
            onChange={(v) => setCabin(v as (typeof CABINS)[number]["value"])}
            options={CABINS.map((c) => ({ value: c.value, label: c.label }))}
          />{" "}
          class to{" "}
          <InlineSelect
            ariaLabel="Destination"
            value={destination}
            onChange={setDestination}
            options={DESTINATIONS.map((d) => ({ value: d, label: d }))}
          />{" "}
          from{" "}
          <InlineSelect
            ariaLabel="Flying from"
            value={origin}
            onChange={setOrigin}
            options={ORIGINS.map((o) => ({ value: o, label: o }))}
          />{" "}
          within{" "}
          <span className="inline-flex items-baseline gap-1 whitespace-nowrap">
            <input
              type="number"
              min={1}
              max={36}
              value={timeline}
              onChange={(e) => setTimeline(e.target.value)}
              aria-label="Timeline in months"
              className="w-16 rounded-none border-0 border-b border-gold/50 bg-transparent px-1 text-center font-heading italic text-gold focus:border-gold focus:outline-none"
            />
            months
          </span>
          , for{" "}
          <InlineSelect
            ariaLabel="Passengers"
            value={String(passengers)}
            onChange={(v) => setPassengers(Number(v))}
            options={PASSENGERS.map((n) => ({
              value: String(n),
              label: n === 1 ? "1 passenger" : `${n} passengers`,
            }))}
          />
          .
        </p>
      </div>

      {/* ── Your situation: cards, spend, appetite for new cards ── */}
      <div className="p-6 sm:p-8">
        {cardsByBank.length > 0 && (
          <div className="space-y-4">
            <Label className="text-base font-semibold text-foreground">
              Cards you already hold
            </Label>
            <div className="grid gap-x-8 gap-y-5 sm:grid-cols-2">
              {cardsByBank.map(([bank, bankCards]) => (
                <div key={bank}>
                  <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground/80">
                    {bank}
                  </p>
                  <div className="mt-2.5 flex flex-wrap gap-2">
                    {bankCards.map((card) => {
                      const selected = selectedCardIds.includes(card.id);
                      return (
                        <button
                          key={card.id}
                          type="button"
                          onClick={() => toggleCard(card.id)}
                          aria-pressed={selected}
                          className={`flex items-center gap-2 rounded-xl border px-3.5 py-2 text-sm font-medium transition-all ${
                            selected
                              ? "border-gold/50 bg-gold/10 text-gold"
                              : "border-hairline bg-input/20 text-muted-foreground hover:border-white/25 hover:text-foreground"
                          }`}
                        >
                          <span
                            aria-hidden="true"
                            className={`grid size-4 shrink-0 place-items-center rounded-full border transition-colors ${
                              selected
                                ? "border-gold bg-gold text-gold-foreground"
                                : "border-white/25 text-transparent"
                            }`}
                          >
                            <Check className="size-3" strokeWidth={3} />
                          </span>
                          {card.card_name}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="mt-8 space-y-2.5">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <Label className="text-base font-semibold text-foreground">
              What you spend in a month
            </Label>
            <span className="text-sm tabular-nums text-muted-foreground">
              Total ₹{totalSpend.toLocaleString("en-IN")}/mo
            </span>
          </div>
          <p className="text-sm text-muted-foreground">
            The engine routes each category to the card that earns it best —
            rough numbers are fine.
          </p>
          <div className="grid gap-x-8 gap-y-2.5 pt-1 sm:grid-cols-2">
            {SPEND_CATEGORIES.map((c) => (
              <div key={c.slug} className="flex items-center justify-between gap-3">
                <Label
                  htmlFor={`spend-${c.slug}`}
                  className="text-[15px] font-normal text-foreground/90"
                >
                  {c.label}
                </Label>
                <div className="flex items-center gap-1.5">
                  <span className="text-[15px] text-muted-foreground">₹</span>
                  <Input
                    id={`spend-${c.slug}`}
                    type="number"
                    min={0}
                    step={1000}
                    value={spend[c.slug]}
                    onChange={(e) =>
                      setSpend((prev) => ({ ...prev, [c.slug]: e.target.value }))
                    }
                    className="h-10 w-32 bg-input/30 text-right text-[15px]! tabular-nums"
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-8 space-y-2.5">
          <Label className="text-base font-semibold text-foreground">
            Open to adding a new card?
          </Label>
          <div className="inline-flex rounded-lg border border-hairline bg-input/20 p-1">
            {[
              { label: "Yes, show me options", value: true },
              { label: "Prefer to use my cards", value: false },
            ].map((opt) => (
              <button
                key={String(opt.value)}
                type="button"
                onClick={() => setOpenToNewCards(opt.value)}
                aria-pressed={openToNewCards === opt.value}
                className={`rounded-md px-5 py-2 text-sm font-medium transition-colors ${
                  openToNewCards === opt.value
                    ? "bg-gold text-gold-foreground"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

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

        {/* scroll-mt clears the app shell's sticky top bar when auto-scrolled. */}
        <div aria-live="polite" ref={resultRef} className="scroll-mt-24">
          {loading && (
            <div className="mt-8 rounded-2xl border border-hairline bg-background/40 p-4 sm:p-6">
              <PlaneLoader />
            </div>
          )}
          {!loading && response && (
            <SimulatorResult
              response={response}
              destination={destination}
              cardNames={cardNames}
              horizonMonths={lastRequest?.intent.timeline_months ?? null}
              preferNoNewCards={!openToNewCards}
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

/** A select disguised as the emphasized word in the goal sentence — the form
 * IS the sentence, so entering the goal reads like saying it. */
function InlineSelect({
  value,
  onChange,
  options,
  ariaLabel,
}: {
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  ariaLabel: string;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      aria-label={ariaLabel}
      className="max-w-full appearance-none rounded-none border-0 border-b border-gold/50 bg-transparent px-1 pb-0.5 font-heading italic text-gold focus:border-gold focus:outline-none"
    >
      {options.map((o) => (
        <option key={o.value} value={o.value} className="bg-card font-sans not-italic">
          {o.label}
        </option>
      ))}
    </select>
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

function SimulatorResult({
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

  // Feasible → the full narrative (verdict, route tabs, plan steps, chart,
  // why). Infeasible → an honest verdict plus the adjustment menu.
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
