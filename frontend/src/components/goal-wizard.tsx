"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowRight, Check, Pencil, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PlaneLoader } from "@/components/ui/plane-loader";
import {
  ApiError,
  fetchCards,
  fetchEducation,
  fetchEducationStory,
  probeFeasibility,
  simulate,
  simulateAndSave,
  type CardSummary,
  type EducationPayload,
  type FeasibilityVerdict,
  type SimulateRequest,
  type SimulateResponse,
} from "@/lib/api";
import { SaveGoal, SimulatorResult } from "@/components/wizard/result";
import { EducationStory } from "@/components/wizard/education-step";
import {
  prefillSplit,
  SPLIT_CATEGORIES,
  SplitStep,
} from "@/components/wizard/split-step";
import { AdjustmentMenu } from "@/components/strategy-story";
import { getAccessToken } from "@/lib/supabase";
import { useAuth } from "@/lib/use-auth";

/**
 * The guided strategy wizard (decision log 2026-07-13): one
 * conversational-scroll page — goal sentence → wallet → total spend →
 * education → opt-in split → strategy. Each completed step collapses to an
 * editable summary line; the next appears below and auto-scrolls into view.
 * Editing an earlier step invalidates everything computed after it (inputs
 * are kept, results are discarded). All state is client-held — nothing
 * persists until the user saves the finished strategy.
 *
 * - Spend is ONE number for the whole timeline (decision 2); the server
 *   derives the assumed split (slice 1) unless the user engages the split
 *   step, whose numbers then become the truth (decision 7).
 * - A silent feasibility probe fires after the total-spend step (decision
 *   5): clearly hopeless goals are interrupted with the adjustment menu
 *   before education; anything else passes invisibly, and a probe failure
 *   never blocks the flow.
 * - An empty wallet skips standalone education (decision 13) — a one-liner
 *   replaces the step and the recommended acquisition's education renders
 *   with the strategy output instead.
 */

// Backend-supported vocabulary (goal_resolution.CITY_TO_REGION).
const DESTINATIONS = ["Singapore", "London", "New York"];
const ORIGINS = ["Hyderabad", "Mumbai", "Delhi", "Bangalore", "Chennai", "Pune"];
const PASSENGERS = [1, 2, 3, 4];
const CABINS = [
  { label: "economy", value: "economy" },
  { label: "business", value: "business" },
  { label: "first", value: "first" },
] as const;

type CabinValue = (typeof CABINS)[number]["value"];
type StepId = "goal" | "wallet" | "budget" | "education" | "split" | "strategy";

export function GoalWizard() {
  // ── Step inputs (kept across edits — editing invalidates results, not data)
  const [origin, setOrigin] = useState(ORIGINS[0]);
  const [destination, setDestination] = useState(DESTINATIONS[0]);
  const [cabin, setCabin] = useState<CabinValue>("business");
  const [timeline, setTimeline] = useState("8");
  const [passengers, setPassengers] = useState(1);
  const [selectedCardIds, setSelectedCardIds] = useState<string[]>([]);
  const [totalSpend, setTotalSpend] = useState("");
  const [splitEngaged, setSplitEngaged] = useState<boolean | null>(null);
  const [splitValues, setSplitValues] = useState<Record<string, string>>({});

  const [cards, setCards] = useState<CardSummary[]>([]);
  const [activeStep, setActiveStep] = useState<StepId>("goal");

  // ── Probe gate (slice 5): set only when the goal is clearly hopeless.
  const [probing, setProbing] = useState(false);
  const [probeBlock, setProbeBlock] = useState<{
    verdict: FeasibilityVerdict;
    milesRequired: number;
  } | null>(null);

  // ── Education payload (slice 6), cached per wallet selection.
  const [education, setEducation] = useState<EducationPayload | null>(null);
  const [educationFor, setEducationFor] = useState("");
  const [educationFailed, setEducationFailed] = useState(false);
  // LLM framing (decision 10) — fetched separately so it can never delay the
  // deterministic render; null is the norm without a live LLM key.
  const [educationStory, setEducationStory] = useState<string | null>(null);

  // ── Final-step run state
  const [response, setResponse] = useState<SimulateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastRequest, setLastRequest] = useState<SimulateRequest | null>(null);
  // Education for the RECOMMENDED acquisitions — the deferred education an
  // empty-wallet journey gets with its strategy (decision 13).
  const [acquiredEducation, setAcquiredEducation] = useState<EducationPayload | null>(null);
  const [saveState, setSaveState] = useState<
    "idle" | "saving" | "saved" | "error" | "session_expired"
  >("idle");
  // The persisted goal's id from a landed save — links "Saved ✓" straight to
  // the saved goal instead of the dashboard list.
  const [savedGoalId, setSavedGoalId] = useState<string | null>(null);
  const { user, loading: authLoading } = useAuth();

  const months = Math.max(Number(timeline) || 1, 1);
  const totalSpendValue = Math.max(Math.round(Number(totalSpend) || 0), 0);
  const monthlyApprox = totalSpendValue > 0 ? Math.floor(totalSpendValue / months) : 0;

  const cardNames = new Map(cards.map((c) => [c.id, c.card_name]));

  // The step sequence is dynamic: an empty wallet has no standalone
  // education step (decision 13 — a one-liner replaces it).
  const hasEducation = selectedCardIds.length > 0;
  const sequence: StepId[] = [
    "goal",
    "wallet",
    "budget",
    ...(hasEducation ? (["education"] as StepId[]) : []),
    "split",
    "strategy",
  ];
  const activeIndex = sequence.indexOf(activeStep);
  const indexOf = (id: StepId) => sequence.indexOf(id);
  const stateOf = (id: StepId): StepState => {
    const index = indexOf(id);
    if (index === activeIndex) return "active";
    return index !== -1 && index < activeIndex ? "done" : "pending";
  };

  // Auto-scroll the newly active step into view (decision 11). Skipped on
  // first render so loading the page never yanks the viewport; reduced
  // motion falls back to an instant jump.
  const activeStepRef = useRef<HTMLDivElement>(null);
  const hasInteracted = useRef(false);
  useEffect(() => {
    if (!hasInteracted.current || !activeStepRef.current) return;
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    activeStepRef.current.scrollIntoView({
      behavior: reduceMotion ? "auto" : "smooth",
      block: "start",
    });
  }, [activeStep]);

  // Load the catalog for the wallet picker; pre-select the flagship cards.
  useEffect(() => {
    let active = true;
    fetchCards()
      .then((fetched) => {
        if (!active) return;
        setCards(fetched);
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

  // Fetch the wallet's reward story when the education step opens (pure
  // catalog read — instant). A failure renders a soft fallback, never a wall.
  useEffect(() => {
    if (activeStep !== "education" || selectedCardIds.length === 0) return;
    const key = [...selectedCardIds].sort().join(",");
    if (educationFor === key && (education || educationFailed)) return;
    let active = true;
    fetchEducation(selectedCardIds)
      .then((payload) => {
        if (!active) return;
        setEducation(payload);
        setEducationFor(key);
        setEducationFailed(false);
      })
      .catch(() => {
        if (!active) return;
        setEducation(null);
        setEducationFor(key);
        setEducationFailed(true);
      });
    // The LLM framing rides in parallel (decision 10) — it lands on top when
    // available and its absence/failure changes nothing. The resolved value
    // replaces any previous wallet's story (null clears it).
    fetchEducationStory(selectedCardIds)
      .then((story) => {
        if (active) setEducationStory(story);
      })
      .catch(() => {
        if (active) setEducationStory(null);
      });
    return () => {
      active = false;
    };
  }, [activeStep, selectedCardIds, education, educationFailed, educationFor]);

  // Deferred education (decision 13): an empty-wallet strategy leads with
  // the recommended acquisition's reward story. (Stale payloads are cleared
  // in runStrategy, so this effect only ever fetches.)
  useEffect(() => {
    if (selectedCardIds.length > 0) return;
    if (response?.kind !== "recommendation") return;
    const acquire = response.recommendation.recommended?.strategy.cards_to_acquire ?? [];
    if (acquire.length === 0) return;
    let active = true;
    fetchEducation(acquire)
      .then((payload) => {
        if (active) setAcquiredEducation(payload);
      })
      .catch(() => {
        // Enhancement only — the strategy stands on its own.
      });
    return () => {
      active = false;
    };
    // selectedCardIds is deliberately read, not depended on: the wallet that
    // matters is the one the response was built with.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [response]);

  function goTo(step: StepId) {
    hasInteracted.current = true;
    setActiveStep(step);
  }

  /** Reopen an earlier step: keep its inputs, discard everything computed
   * after it (decision 11 — editing invalidates downstream). */
  function editStep(step: StepId) {
    setResponse(null);
    setError(null);
    setLastRequest(null);
    setSaveState("idle");
    setProbeBlock(null);
    goTo(step);
  }

  function buildRequest(split: Record<string, string> | null): SimulateRequest {
    const base: SimulateRequest = {
      intent: {
        origin_city: origin,
        destination_city: destination,
        cabin_class: cabin,
        timeline_months: months,
        num_passengers: passengers,
        confidence: 1,
      },
      wallet: selectedCardIds.map((id) => ({
        card_id: id,
        current_points_balance: 0,
      })),
    };
    if (split) {
      // The user's split is the truth (decision 7): horizon totals become
      // the engine's monthly amounts (floored, like every projection input).
      const profile = SPLIT_CATEGORIES.map((c) => ({
        category_slug: c.slug,
        monthly_spend_inr: Math.floor(
          Math.max(Math.round(Number(split[c.slug]) || 0), 0) / months,
        ),
      })).filter((item) => item.monthly_spend_inr > 0);
      return profile.length > 0 ? { ...base, spend_profile: profile } : base;
    }
    // No split engaged: one total for the horizon (decision 2–3); the SERVER
    // derives the assumed split. Blank ⇒ the engine's flagged default.
    return totalSpendValue > 0
      ? { ...base, total_spend_inr: totalSpendValue }
      : base;
  }

  /** Slice 5: the silent early check. Hopeless → interrupt with the menu;
   * anything else (including a probe failure) passes invisibly. */
  async function continueFromBudget() {
    setProbing(true);
    let blocked = false;
    try {
      const result = await probeFeasibility(buildRequest(null));
      if (result.kind === "feasibility" && !result.verdict.feasible) {
        setProbeBlock({
          verdict: result.verdict,
          milesRequired: result.miles_required_total,
        });
        blocked = true;
      }
    } catch {
      // The probe is an enhancement — never block the flow on its failure.
    } finally {
      setProbing(false);
    }
    if (!blocked) {
      setProbeBlock(null);
      goTo(hasEducation ? "education" : "split");
    }
  }

  async function runStrategy(split: Record<string, string> | null) {
    goTo("strategy");
    setLoading(true);
    setError(null);
    setResponse(null);
    setAcquiredEducation(null);
    setSaveState("idle");
    const request = buildRequest(split);
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
        setSaveState("session_expired");
        return;
      }
      const result = await simulateAndSave(lastRequest, token);
      const saved = result.kind === "recommendation" && result.persisted === true;
      setSavedGoalId(saved ? (result.saved_goal_id ?? null) : null);
      setSaveState(saved ? "saved" : "error");
    } catch {
      setSaveState("error");
    }
  }

  /** One-click refine from the assumed-split caveat (decision 6): reopen the
   * split step with the editor already engaged and pre-filled. */
  function refineSplit() {
    setSplitEngaged(true);
    if (Object.keys(splitValues).length === 0) {
      setSplitValues(prefillSplit(splitBasis()));
    }
    editStep("split");
  }

  function splitBasis(): number {
    // Scale the template to the user's total; with no total, fall back to
    // the template's own monthly sum over the horizon.
    return totalSpendValue > 0 ? totalSpendValue : 90_000 * months;
  }

  const goalSummary = `${cabin} class to ${destination} from ${origin} · ${months} ${
    months === 1 ? "month" : "months"
  } · ${passengers} ${passengers === 1 ? "passenger" : "passengers"}`;
  const walletSummary =
    selectedCardIds.length === 0
      ? "No cards yet"
      : selectedCardIds.map((id) => cardNames.get(id) ?? "Card").join(", ");
  const budgetSummary =
    totalSpendValue > 0
      ? `₹${totalSpendValue.toLocaleString("en-IN")} over ${months} ${
          months === 1 ? "month" : "months"
        } (≈ ₹${monthlyApprox.toLocaleString("en-IN")}/month)`
      : "Typical spending profile (assumed)";
  const educationSummary =
    education && educationFor === [...selectedCardIds].sort().join(",")
      ? education.shared_partners.length > 0
        ? `How your cards earn — ${education.shared_partners
            .map((p) => p.program_name)
            .join(", ")} in common`
        : "How your cards earn"
      : "How your cards earn";
  const splitTotal = SPLIT_CATEGORIES.reduce(
    (sum, c) => sum + Math.max(Math.round(Number(splitValues[c.slug]) || 0), 0),
    0,
  );
  const splitSummary =
    splitEngaged === true
      ? `Your split: ₹${splitTotal.toLocaleString("en-IN")} over ${months} ${
          months === 1 ? "month" : "months"
        }`
      : "Typical split (assumed)";

  const assumedSpend =
    response?.kind === "recommendation" &&
    response.recommendation.assumed_flags.includes("spend_profile");

  return (
    <div className="overflow-hidden rounded-[2rem] border border-white/10 bg-card/60 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] backdrop-blur-sm">
      {/* ── Step 1: the goal, as the sentence you'd say out loud ── */}
      <WizardStep
        number={1}
        title="Your goal"
        icon={<Sparkles className="size-3.5" />}
        state={stateOf("goal")}
        summary={goalSummary}
        onEdit={() => editStep("goal")}
        stepRef={activeStep === "goal" ? activeStepRef : undefined}
      >
        <p className="mt-4 font-heading text-2xl leading-[2.1] text-foreground sm:text-3xl sm:leading-loose">
          I want to fly{" "}
          <InlineSelect
            ariaLabel="Cabin class"
            value={cabin}
            onChange={(v) => setCabin(v as CabinValue)}
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
        <Button
          onClick={() => goTo("wallet")}
          className="mt-6 bg-gold text-gold-foreground hover:bg-gold/90"
        >
          Continue
          <ArrowRight />
        </Button>
      </WizardStep>

      {/* ── Step 2: the wallet ── */}
      {activeIndex >= indexOf("wallet") && (
        <WizardStep
          number={2}
          title="Cards you already hold"
          state={stateOf("wallet")}
          summary={walletSummary}
          onEdit={() => editStep("wallet")}
          stepRef={activeStep === "wallet" ? activeStepRef : undefined}
        >
          {cards.length > 0 ? (
            <div className="mt-4 grid gap-x-8 gap-y-5 sm:grid-cols-2">
              {groupByBank(cards).map(([bank, bankCards]) => (
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
                          onClick={() =>
                            setSelectedCardIds((prev) =>
                              prev.includes(card.id)
                                ? prev.filter((c) => c !== card.id)
                                : [...prev, card.id],
                            )
                          }
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
          ) : (
            <p className="mt-4 text-sm text-muted-foreground">
              Couldn&apos;t load the card catalog — you can continue with no
              cards and we&apos;ll recommend the right ones.
            </p>
          )}
          {selectedCardIds.length === 0 && cards.length > 0 && (
            <p className="mt-4 text-sm text-muted-foreground">
              No cards yet? That&apos;s fine — we&apos;ll introduce the right
              ones with your strategy.
            </p>
          )}
          <Button
            onClick={() => goTo("budget")}
            className="mt-6 bg-gold text-gold-foreground hover:bg-gold/90"
          >
            Continue
            <ArrowRight />
          </Button>
        </WizardStep>
      )}

      {/* ── Step 3: total spend over the horizon (decision 2) ── */}
      {activeIndex >= indexOf("budget") && (
        <WizardStep
          number={3}
          title="Your spending"
          state={stateOf("budget")}
          summary={budgetSummary}
          onEdit={() => editStep("budget")}
          stepRef={activeStep === "budget" ? activeStepRef : undefined}
        >
          <p className="mt-3 max-w-2xl text-sm text-muted-foreground">
            Roughly how much will you put on your cards over the next{" "}
            {months} {months === 1 ? "month" : "months"}, in total? A ballpark
            is fine — we&apos;ll route it across categories for you.
          </p>
          <div className="mt-4 flex items-center gap-2">
            <span className="text-lg text-muted-foreground">₹</span>
            <Input
              type="number"
              min={0}
              step={10000}
              value={totalSpend}
              onChange={(e) => {
                setTotalSpend(e.target.value);
                setProbeBlock(null);
              }}
              placeholder={`e.g. ${(months * 100_000).toLocaleString("en-IN")}`}
              aria-label={`Total spend over ${months} months, in rupees`}
              className="h-12 w-56 bg-input/30 text-right text-lg! tabular-nums"
            />
          </div>
          {/* The even-spread assumption, made visible (decision 2). */}
          {totalSpendValue > 0 ? (
            <p className="mt-2.5 text-sm text-muted-foreground">
              ≈ ₹{monthlyApprox.toLocaleString("en-IN")}/month — we assume even
              spending.
            </p>
          ) : (
            <p className="mt-2.5 text-sm text-muted-foreground">
              Leave it blank and we&apos;ll assume a typical spending profile
              (you can refine it later).
            </p>
          )}
          <Button
            onClick={continueFromBudget}
            disabled={probing}
            className="mt-6 bg-gold text-gold-foreground hover:bg-gold/90 disabled:opacity-60"
          >
            Continue
            <ArrowRight />
          </Button>

          {/* Slice 5: the early interrupt for clearly hopeless goals — the
              menu is the answer, and every step above stays editable. */}
          {probeBlock && (
            <div
              role="alert"
              className="mt-6 max-w-3xl rounded-2xl border border-destructive/40 bg-destructive/5 p-5"
            >
              <p className="font-heading text-xl text-foreground">
                This goal isn&apos;t reachable as stated
              </p>
              <p className="mt-1.5 text-sm text-muted-foreground">
                Even with the best available cards, you&apos;d top out around{" "}
                <span className="tabular-nums text-foreground">
                  {probeBlock.verdict.best_case_miles.toLocaleString("en-IN")}
                </span>{" "}
                of the{" "}
                <span className="tabular-nums text-foreground">
                  {probeBlock.milesRequired.toLocaleString("en-IN")}
                </span>{" "}
                miles needed in {months} {months === 1 ? "month" : "months"}.
              </p>
              <div className="mt-4">
                <AdjustmentMenu options={probeBlock.verdict.adjustment_options} />
              </div>
              <p className="mt-4 text-sm text-muted-foreground">
                Adjust the goal, timeline, or spending above — every step stays
                editable.
              </p>
            </div>
          )}
        </WizardStep>
      )}

      {/* ── Step 4: education (skipped for an empty wallet, decision 13) ── */}
      {hasEducation && activeIndex >= indexOf("education") && (
        <WizardStep
          number={4}
          title="How your cards earn"
          state={stateOf("education")}
          summary={educationSummary}
          onEdit={() => editStep("education")}
          stepRef={activeStep === "education" ? activeStepRef : undefined}
        >
          {education && educationFor === [...selectedCardIds].sort().join(",") ? (
            <EducationStory payload={education} narrative={educationStory} />
          ) : educationFailed ? (
            <p className="mt-4 text-sm text-muted-foreground">
              Couldn&apos;t load your cards&apos; reward story right now — the
              strategy itself isn&apos;t affected.
            </p>
          ) : (
            <p className="mt-4 text-sm text-muted-foreground">
              Reading your cards&apos; reward rules…
            </p>
          )}
          <Button
            onClick={() => goTo("split")}
            className="mt-6 bg-gold text-gold-foreground hover:bg-gold/90"
          >
            Continue
            <ArrowRight />
          </Button>
        </WizardStep>
      )}
      {!hasEducation && activeIndex > indexOf("budget") && (
        <div className="border-b border-hairline px-6 py-4 sm:px-8">
          <p className="text-sm text-muted-foreground">
            No cards yet — we&apos;ll introduce the right ones with your
            strategy.
          </p>
        </div>
      )}

      {/* ── Step 5: the opt-in split (decisions 6–7) ── */}
      {activeIndex >= indexOf("split") && (
        <WizardStep
          number={hasEducation ? 5 : 4}
          title="Want a spending strategy?"
          state={stateOf("split")}
          summary={splitSummary}
          onEdit={() => {
            if (splitEngaged) {
              refineSplit();
            } else {
              editStep("split");
            }
          }}
          stepRef={activeStep === "split" ? activeStepRef : undefined}
        >
          <SplitStep
            months={months}
            engaged={splitEngaged}
            values={splitValues}
            onEngage={() => {
              setSplitEngaged(true);
              if (Object.keys(splitValues).length === 0) {
                setSplitValues(prefillSplit(splitBasis()));
              }
            }}
            onDecline={() => {
              setSplitEngaged(false);
              void runStrategy(null);
            }}
            onChange={(slug, value) =>
              setSplitValues((prev) => ({ ...prev, [slug]: value }))
            }
            onBuild={() => void runStrategy(splitValues)}
            building={loading}
          />
        </WizardStep>
      )}

      {/* ── Step 6: the strategy ── */}
      {activeIndex >= indexOf("strategy") && (
        <WizardStep
          number={hasEducation ? 6 : 5}
          title="Your strategy"
          state="active"
          summary=""
          stepRef={activeStep === "strategy" ? activeStepRef : undefined}
        >
          <div aria-live="polite">
            {loading && (
              <div className="mt-4 rounded-2xl border border-hairline bg-background/40 p-4 sm:p-6">
                <PlaneLoader />
              </div>
            )}
            {error && (
              <div className="mt-4">
                <p className="text-sm text-destructive" role="alert">
                  {error}
                </p>
                <Button
                  onClick={() => void runStrategy(splitEngaged ? splitValues : null)}
                  variant="outline"
                  className="mt-3 border-gold/40 text-gold hover:bg-gold/10"
                >
                  Try again
                </Button>
              </div>
            )}
            {/* Declined/absent split ⇒ the numbers below rest on an assumed
                split — say so, with the one-click way back (decision 6). */}
            {!loading && response && assumedSpend && (
              <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-2 rounded-xl border border-hairline bg-background/40 px-4 py-3">
                <p className="text-sm text-muted-foreground">
                  Built on an assumed split of your spending.
                </p>
                <button
                  type="button"
                  onClick={refineSplit}
                  className="text-sm font-medium text-gold hover:underline"
                >
                  Refine the split →
                </button>
              </div>
            )}
            {/* Deferred education for an empty wallet (decision 13): meet the
                recommended cards before the plan that uses them. */}
            {!loading && acquiredEducation && (
              <div className="mt-4">
                <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
                  Meet your recommended {acquiredEducation.cards.length === 1 ? "card" : "cards"}
                </p>
                <EducationStory payload={acquiredEducation} />
              </div>
            )}
            {!loading && response && (
              <SimulatorResult
                response={response}
                destination={destination}
                cardNames={cardNames}
                horizonMonths={lastRequest?.intent.timeline_months ?? null}
                preferNoNewCards={false}
              />
            )}
          </div>
          {response?.kind === "recommendation" && lastRequest && !authLoading && (
            <SaveGoal
              isLoggedIn={Boolean(user)}
              state={saveState}
              savedGoalId={savedGoalId}
              onSave={handleSave}
            />
          )}
        </WizardStep>
      )}
    </div>
  );
}

type StepState = "active" | "done" | "pending";

/** One conversational-scroll step: full while active, an editable one-line
 * summary once completed. `scroll-mt` clears the app shell's sticky bar when
 * the auto-scroll lands here. */
function WizardStep({
  number,
  title,
  icon,
  state,
  summary,
  onEdit,
  stepRef,
  children,
}: {
  number: number;
  title: string;
  icon?: React.ReactNode;
  state: StepState;
  summary: string;
  onEdit?: () => void;
  stepRef?: React.Ref<HTMLDivElement>;
  children: React.ReactNode;
}) {
  if (state === "done") {
    return (
      <div className="flex items-center justify-between gap-4 border-b border-hairline px-6 py-4 sm:px-8">
        <div className="flex min-w-0 items-center gap-3">
          <span
            aria-hidden="true"
            className="grid size-7 shrink-0 place-items-center rounded-full border border-gold/40 bg-gold/10 text-gold"
          >
            <Check className="size-3.5" strokeWidth={3} />
          </span>
          <div className="min-w-0">
            <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
              {title}
            </p>
            <p className="truncate text-sm text-foreground">{summary}</p>
          </div>
        </div>
        {onEdit && (
          <button
            type="button"
            onClick={onEdit}
            className="flex shrink-0 items-center gap-1.5 rounded-lg border border-hairline px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:border-gold/40 hover:text-gold"
          >
            <Pencil className="size-3.5" aria-hidden="true" />
            Edit
          </button>
        )}
      </div>
    );
  }

  return (
    <div
      ref={stepRef}
      className="scroll-mt-24 border-b border-hairline px-6 py-6 last:border-b-0 sm:px-8"
    >
      <p className="flex items-center gap-2 text-xs uppercase tracking-[0.12em] text-muted-foreground">
        <span className="grid size-7 shrink-0 place-items-center rounded-lg border border-gold/30 bg-gold/10 text-gold">
          {icon ?? <span className="text-xs font-semibold">{number}</span>}
        </span>
        {title}
      </p>
      {children}
    </div>
  );
}

function groupByBank(cards: CardSummary[]): [string, CardSummary[]][] {
  const groups: [string, CardSummary[]][] = [];
  for (const card of cards) {
    const group = groups.find(([bank]) => bank === card.bank);
    if (group) group[1].push(card);
    else groups.push([card.bank, [card]]);
  }
  return groups;
}

/** A select disguised as the emphasized word in the goal sentence — the form
 * IS the sentence, so entering the goal reads like saying it. (Moved here
 * from the retired one-shot simulator, slice 10.) */
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
