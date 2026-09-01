"use client";

import { useEffect, useMemo, useState } from "react";

import { Bleed, Inner } from "@/components/sections/section-shell";
import { CardPicker } from "@/components/ui/card-picker";
import { PlaneLoader } from "@/components/ui/plane-loader";
import { ProgramChooser } from "@/components/ui/program-chooser";
import { useWallet } from "@/lib/wallet";
import {
  ApiError,
  SPEND_CATEGORIES,
  fetchBestCard,
  fetchCards,
  type BestCardResult,
  type CardSpendOption,
  type CardSummary,
  type SpendCategorySlug,
} from "@/lib/api";

const inr = new Intl.NumberFormat("en-IN");

/**
 * Best Card for this Spend — the Phase 1 daily-surface hook.
 *
 * THREE STEPS, and the first one makes no assumptions:
 *
 *   1. Points — what each card earns for this spend, in its own currency,
 *      with the maths. NO winner is crowned here, because across currencies
 *      there isn't an honest one: HDFC RP, EDGE Miles and MR are different
 *      units and the catalog carries no ₹-per-point valuation to convert
 *      them. Saying "use this one" at this stage would be a guess.
 *   2. Ask — "want to see what these are worth if you transfer?"
 *   3. The user picks a program, and only then does the ranking appear, in
 *      the unit they chose. That's where the real insight lives: when the
 *      points order and the miles order disagree, the disagreement IS the
 *      answer, and the runner-up callout is where someone learns their
 *      instinct was wrong.
 *
 * An earlier version skipped straight to step 3 with KrisFlyer assumed,
 * because the retired MVP scope named it primary — so the page told users
 * about a program they had never mentioned. See `CLAUDE.md` → *Never Assume
 * the User's Goal*.
 */
export function BestCard() {
  const { cardIds: wallet, setWallet } = useWallet();
  const [cards, setCards] = useState<CardSummary[]>([]);
  // The picker starts as the user's saved wallet and becomes a local
  // what-if the moment they touch it — derived, not copied into state by an
  // effect, so a wallet saved in another tab shows up here immediately and
  // there is no hydration flash. `null` means "still just the wallet".
  const [override, setOverride] = useState<string[] | null>(null);
  const selectedIds = useMemo(
    () => override ?? [...wallet],
    [override, wallet],
  );
  const [amount, setAmount] = useState("10000");
  const [category, setCategory] = useState<SpendCategorySlug>("default");
  // null = the user hasn't chosen where their points are going, which is the
  // default state and a legitimate answer, not a missing input.
  const [programId, setProgramId] = useState<string | null>(null);

  const [result, setResult] = useState<BestCardResult | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCards()
      .then(setCards)
      .catch(() => setError("Couldn't load the card catalog."));
  }, []);

  const amountInr = Number.parseInt(amount, 10);
  const ready =
    selectedIds.length > 0 && Number.isFinite(amountInr) && amountInr > 0;

  // Re-price whenever the inputs change — the endpoint is a pure snapshot
  // read with no LLM and no DB, so there is no reason to make the user press
  // a button to see their own answer.
  useEffect(() => {
    // No setState here on the not-ready path: the render below already shows
    // the empty state whenever `ready` is false, so a stale result can never
    // be displayed and clearing it would just cascade a render.
    if (!ready) return;
    let cancelled = false;
    // `pending` flips inside the debounce callback rather than in the effect
    // body: it keeps setState out of the synchronous render path, and it also
    // reads better — no loader flicker while the amount is still being typed.
    const timer = setTimeout(() => {
      setPending(true);
      fetchBestCard({
        amountInr,
        category,
        cardIds: selectedIds,
        targetProgramId: programId ?? undefined,
      })
        .then((body) => {
          if (!cancelled) {
            setResult(body);
            setError(null);
          }
        })
        .catch((err: unknown) => {
          if (!cancelled) {
            setResult(null);
            setError(
              err instanceof ApiError ? err.message : "Couldn't work that out.",
            );
          }
        })
        .finally(() => !cancelled && setPending(false));
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [ready, amountInr, category, selectedIds, programId]);

  const toggle = (cardId: string) =>
    setOverride(
      selectedIds.includes(cardId)
        ? selectedIds.filter((c) => c !== cardId)
        : [...selectedIds, cardId],
    );

  // Only offer the save when the picker actually says something new — this
  // surface is a what-if, so it never overwrites the wallet silently.
  const unsaved =
    override !== null &&
    (override.length !== wallet.length ||
      override.some((id) => !wallet.includes(id)));

  return (
    <Bleed className="border-b border-hairline py-14 sm:py-20">
      <Inner>
        <header className="max-w-2xl">
          <p className="text-xs font-medium uppercase tracking-[0.16em] text-gold">
            Best card for this spend
          </p>
          <h1 className="mt-3 text-3xl font-semibold leading-tight sm:text-4xl">
            About to spend something? Swipe the right card.
          </h1>
          <p className="mt-4 text-base leading-relaxed text-muted-foreground">
            Pick the cards you actually hold and we&apos;ll show what each one
            earns on this purchase, with the maths. Points from different banks
            aren&apos;t the same thing — so if you tell us where you want to
            send them, we&apos;ll tell you which card actually wins.
          </p>
        </header>

        <div className="mt-10 grid gap-10 lg:grid-cols-[minmax(0,22rem)_minmax(0,1fr)] lg:gap-14">
          <form
            className="space-y-7"
            onSubmit={(event) => event.preventDefault()}
          >
            <div>
              <label
                htmlFor="amount"
                className="text-sm font-semibold text-foreground"
              >
                How much are you spending?
              </label>
              <div className="mt-2 flex items-center gap-2 rounded-xl border border-hairline bg-input/20 px-3.5 focus-within:border-gold/50">
                <span className="text-lg text-muted-foreground">₹</span>
                <input
                  id="amount"
                  inputMode="numeric"
                  value={amount}
                  onChange={(event) =>
                    setAmount(event.target.value.replace(/[^0-9]/g, ""))
                  }
                  className="h-12 w-full bg-transparent text-lg font-medium outline-none"
                  placeholder="10000"
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="category"
                className="text-sm font-semibold text-foreground"
              >
                On what?
              </label>
              <select
                id="category"
                value={category}
                onChange={(event) =>
                  setCategory(event.target.value as SpendCategorySlug)
                }
                className="mt-2 h-12 w-full rounded-xl border border-hairline bg-input/20 px-3 text-[15px] outline-none focus:border-gold/50"
              >
                {SPEND_CATEGORIES.map((option) => (
                  <option key={option.slug} value={option.slug}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <p className="text-sm font-semibold text-foreground">
                Cards you hold
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                No account needed — this is your real wallet, not a demo.
              </p>
              {unsaved ? (
                <button
                  type="button"
                  onClick={() => {
                    setWallet(selectedIds);
                    setOverride(null);
                  }}
                  className="mt-3 rounded-xl border border-gold/40 bg-gold/10 px-3.5 py-2 text-sm font-medium text-gold transition-colors hover:bg-gold/15"
                >
                  Save these as my cards
                </button>
              ) : null}
              <div className="mt-4">
                {cards.length > 0 ? (
                  <CardPicker
                    cards={cards}
                    selectedIds={selectedIds}
                    onToggle={toggle}
                  />
                ) : (
                  <p className="text-sm text-muted-foreground">
                    Loading cards…
                  </p>
                )}
              </div>
            </div>
          </form>

          <div aria-live="polite">
            {error ? (
              <p className="rounded-xl border border-destructive/40 bg-destructive/5 px-4 py-3 text-sm text-destructive">
                {error}
              </p>
            ) : !ready ? (
              <EmptyState />
            ) : pending && !result ? (
              <div className="flex justify-center py-16">
                <PlaneLoader />
              </div>
            ) : result ? (
              <Result
                result={result}
                programId={programId}
                onSelectProgram={setProgramId}
              />
            ) : null}
          </div>
        </div>
      </Inner>
    </Bleed>
  );
}

function EmptyState() {
  return (
    <div className="rounded-2xl border border-dashed border-hairline px-6 py-14 text-center">
      <p className="text-base text-muted-foreground">
        Pick at least one card to see which one wins.
      </p>
    </div>
  );
}

function Result({
  result,
  programId,
  onSelectProgram,
}: {
  result: BestCardResult;
  programId: string | null;
  onSelectProgram: (id: string | null) => void;
}) {
  const chooser = (
    <ProgramChooser
      reach={result.partner_reach}
      selectedId={programId}
      onSelect={onSelectProgram}
      prompt={
        programId
          ? "Sending these points to"
          : "Want to see what these are worth if you transfer?"
      }
    />
  );

  // Step 1: no program chosen. Report what the catalog states directly and
  // ask — deliberately without naming a winner.
  if (result.ranking_basis === "points") {
    return <PointsFirst result={result} chooser={chooser} />;
  }

  return <Priced result={result} chooser={chooser} />;
}

/** Step 1 — points, in each card's own currency, and no verdict. */
function PointsFirst({
  result,
  chooser,
}: {
  result: BestCardResult;
  chooser: React.ReactNode;
}) {
  return (
    <div className="space-y-8">
      <div>
        <p className="text-xs font-medium uppercase tracking-[0.16em] text-gold">
          What you&apos;d earn
        </p>
        <ul className="mt-3 divide-y divide-hairline rounded-2xl border border-hairline">
          {result.ranked.map((option) => (
            <li key={option.card_id} className="px-4 py-3.5">
              <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                <span className="text-[15px] font-medium">
                  {option.bank} {option.card_name}
                </span>
                <span className="text-[15px] font-semibold tabular-nums">
                  {inr.format(option.points_earned)}{" "}
                  <span className="text-sm font-normal text-muted-foreground">
                    {option.currency_name}
                  </span>
                </span>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                {option.category_label} at {option.effective_earn_rate} per ₹100
                {option.cap_exceeded && option.monthly_cap_inr
                  ? ` · blended down past the ₹${inr.format(option.monthly_cap_inr)}/month cap`
                  : option.monthly_cap_inr
                    ? ` · bonus rate up to ₹${inr.format(option.monthly_cap_inr)}/month`
                    : ""}
              </p>
            </li>
          ))}
        </ul>
      </div>

      {result.ranked.length > 1 ? (
        <p className="rounded-xl border border-hairline bg-input/10 px-4 py-3 text-sm leading-relaxed text-muted-foreground">
          <span className="font-medium text-foreground">
            These aren&apos;t the same unit.
          </span>{" "}
          HDFC Reward Points, EDGE Miles and Membership Rewards are different
          currencies, so the biggest number here isn&apos;t automatically the
          best card. What they&apos;re worth depends on where you send them.
        </p>
      ) : null}

      {chooser}
    </div>
  );
}

/** Step 3 — a program is chosen, so there is a real answer to give. */
function Priced({
  result,
  chooser,
}: {
  result: BestCardResult;
  chooser: React.ReactNode;
}) {
  const [winner, ...rest] = result.ranked;

  // The teaching moment: a card that earns MORE points but FEWER miles.
  const pointsUpset = useMemo(
    () =>
      winner
        ? result.ranked.find(
            (option) => option.points_earned > winner.points_earned,
          )
        : undefined,
    [result.ranked, winner],
  );

  if (!winner) {
    return (
      <div className="space-y-8">
        <div className="rounded-2xl border border-hairline p-6">
          <p className="text-base font-medium">
            None of these cards transfer to {result.target_program_name}.
          </p>
          <p className="mt-2 text-sm text-muted-foreground">
            They still earn rewards — they just can&apos;t reach this program.
          </p>
          <UnroutableList options={result.unroutable} />
        </div>
        {chooser}
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="rounded-2xl border border-gold/40 bg-gold/[0.06] p-6">
        <p className="text-xs font-medium uppercase tracking-[0.14em] text-gold">
          Use this one
        </p>
        <p className="mt-2 text-2xl font-semibold sm:text-3xl">
          {winner.bank} {winner.card_name}
        </p>
        <p className="mt-3 text-base text-muted-foreground">
          Earns{" "}
          <span className="font-semibold text-foreground">
            {inr.format(winner.points_earned)} {winner.currency_name}
          </span>{" "}
          on ₹{inr.format(result.amount_inr)} —{" "}
          <span className="font-semibold text-gold">
            about {inr.format(winner.miles_earned ?? 0)}{" "}
            {result.target_program_name} miles
          </span>
          .
        </p>
        <Maths option={winner} amountInr={result.amount_inr} />
      </div>

      {pointsUpset && pointsUpset.card_id !== winner.card_id ? (
        <p className="rounded-xl border border-hairline bg-input/10 px-4 py-3 text-sm leading-relaxed text-muted-foreground">
          <span className="font-medium text-foreground">Worth knowing:</span>{" "}
          {pointsUpset.card_name} earns more points here (
          {inr.format(pointsUpset.points_earned)} vs{" "}
          {inr.format(winner.points_earned)}) but fewer{" "}
          {result.target_program_name} miles, because it transfers at a worse
          ratio. Points across banks aren&apos;t the same unit — miles are.
        </p>
      ) : null}

      {rest.length > 0 ? (
        <div>
          <p className="text-sm font-semibold text-foreground">
            The rest of your wallet
          </p>
          <ul className="mt-3 divide-y divide-hairline rounded-xl border border-hairline">
            {rest.map((option) => (
              <li
                key={option.card_id}
                className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 px-4 py-3"
              >
                <span className="text-[15px] font-medium">
                  {option.card_name}
                </span>
                <span className="text-sm text-muted-foreground">
                  {inr.format(option.points_earned)} {option.currency_name} →{" "}
                  <span className="text-foreground">
                    {inr.format(option.miles_earned ?? 0)} miles
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <UnroutableList options={result.unroutable} />

      {chooser}

      <p className="text-xs leading-relaxed text-muted-foreground/80">
        Miles shown are what this spend adds to your balance — you transfer in
        blocks later, so the exact credited amount depends on your balance at
        transfer time. Monthly caps are assumed unused.
      </p>
    </div>
  );
}

function Maths({
  option,
  amountInr,
}: {
  option: CardSpendOption;
  amountInr: number;
}) {
  return (
    <div className="mt-5 border-t border-gold/20 pt-4 text-sm text-muted-foreground">
      <p>
        <span className="text-foreground">{option.category_label}</span> at{" "}
        {option.effective_earn_rate} per ₹100 × ₹{inr.format(amountInr)} ={" "}
        {inr.format(option.points_earned)} {option.currency_name}
        {option.miles_per_100
          ? ` → ${option.miles_per_100} miles per ₹100`
          : null}
      </p>
      {option.cap_exceeded && option.monthly_cap_inr ? (
        <p className="mt-2 text-amber-300/90">
          This is above the ₹{inr.format(option.monthly_cap_inr)}/month bonus
          cap, so the rate shown is already blended down to the base rate.
        </p>
      ) : option.monthly_cap_inr ? (
        <p className="mt-2">
          Bonus rate applies up to ₹{inr.format(option.monthly_cap_inr)}/month.
        </p>
      ) : null}
    </div>
  );
}

function UnroutableList({ options }: { options: CardSpendOption[] }) {
  if (options.length === 0) return null;
  return (
    <div>
      <p className="text-sm font-semibold text-foreground">
        No route to this program
      </p>
      <ul className="mt-3 divide-y divide-hairline rounded-xl border border-hairline">
        {options.map((option) => (
          <li
            key={option.card_id}
            className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 px-4 py-3"
          >
            <span className="text-[15px] font-medium">{option.card_name}</span>
            <span className="text-sm text-muted-foreground">
              {inr.format(option.points_earned)} {option.currency_name}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
