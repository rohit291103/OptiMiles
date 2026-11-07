"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, ChevronRight } from "lucide-react";

import { Bleed, Inner } from "@/components/sections/section-shell";
import { CardPicker } from "@/components/ui/card-picker";
import { PlaneLoader } from "@/components/ui/plane-loader";
import { ProgramChooser } from "@/components/ui/program-chooser";
import { useWallet } from "@/lib/wallet";
import { getAccessToken } from "@/lib/supabase";
import { useAuth } from "@/lib/use-auth";
import {
  ApiError,
  SPEND_CATEGORIES,
  fetchBestCard,
  fetchCards,
  fetchSavedGoals,
  type BestCardResult,
  type CardSpendOption,
  type CardSummary,
  type ProgramVerdict,
  type SpendCategorySlug,
} from "@/lib/api";

const inr = new Intl.NumberFormat("en-IN");

/**
 * Best Card for this Spend — the Phase 1 daily-surface hook.
 *
 * 2026-11-07 (decision log `2026-11-07-best-card-verdicts.md`): step 1 now
 * ANSWERS without the user choosing first — a winner per reachable program,
 * each in that program's own unit (still no cross-currency comparison, still
 * no invented ₹ value). Portal-only rates say so and carry the direct-booking
 * alternative; ties and "nobody earns here" are stated, never tiebroken.
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

  const goalProgram = useGoalProgram();
  // Below lg the 9-card picker would push the answer 1.5 screens down; it
  // collapses to a one-line summary with a "Change" button.
  const [pickerOpen, setPickerOpen] = useState(false);

  // The mode travels WITH the result: while a new request is in flight the
  // old result stays on screen, and it must keep the labels it was made for.
  const [shown, setShown] = useState<{ body: BestCardResult; comparingAll: boolean } | null>(
    null,
  );
  const result = shown?.body ?? null;
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCards()
      .then(setCards)
      .catch(() => setError("Couldn't load the card catalog."));
  }, []);

  const amountInr = Number.parseInt(amount, 10);
  // No cards picked → compare every card we cover, so the page answers
  // "which card is best for this?" before the user has said what they hold.
  const comparingAll = selectedIds.length === 0;
  const pricedIds = useMemo(
    () => (comparingAll ? cards.map((c) => c.id) : selectedIds),
    [comparingAll, cards, selectedIds],
  );
  const ready =
    pricedIds.length > 0 && Number.isFinite(amountInr) && amountInr > 0;

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
    const requestedAll = comparingAll;
    const timer = setTimeout(() => {
      setPending(true);
      fetchBestCard({
        amountInr,
        category,
        cardIds: pricedIds,
        targetProgramId: programId ?? undefined,
      })
        .then((body) => {
          if (!cancelled) {
            setShown({ body, comparingAll: requestedAll });
            setError(null);
          }
        })
        .catch((err: unknown) => {
          if (!cancelled) {
            setShown(null);
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
  }, [ready, amountInr, category, pricedIds, programId, comparingAll]);

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
    <Bleed className="border-b border-hairline py-8 sm:py-20">
      <Inner>
        <header className="max-w-2xl">
          <p className="text-xs font-medium uppercase tracking-[0.16em] text-gold">
            Best card for this spend
          </p>
          <h1 className="mt-2 text-[1.65rem] font-semibold leading-tight sm:mt-3 sm:text-4xl">
            About to spend something? Swipe the right card.
          </h1>
          <p className="mt-3 text-[15px] leading-relaxed text-muted-foreground sm:mt-4 sm:text-base">
            Tell us what you&apos;re spending and which cards you hold. We&apos;ll
            say which card to use and what its points become, with the maths.
            Pick no cards and we&apos;ll compare every card we cover.
          </p>
        </header>

        <div className="mt-6 grid gap-6 sm:mt-10 sm:gap-10 lg:grid-cols-[minmax(0,22rem)_minmax(0,1fr)] lg:gap-14">
          <form
            className="space-y-5 sm:space-y-7"
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
              <div className="flex items-baseline justify-between gap-3">
                <p className="text-sm font-semibold text-foreground">
                  Cards you hold
                </p>
                <button
                  type="button"
                  aria-expanded={pickerOpen}
                  aria-controls="card-picker"
                  onClick={() => setPickerOpen((open) => !open)}
                  className="min-h-11 text-sm font-medium text-gold lg:hidden"
                >
                  {pickerOpen ? "Done" : "Change"}
                </button>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                {selectedIds.length === 0
                  ? "None picked — comparing every card we cover."
                  : `${selectedIds.length} picked: ${cards
                      .filter((c) => selectedIds.includes(c.id))
                      .map((c) => c.card_name)
                      .join(", ")}.`}
              </p>
              {unsaved ? (
                <button
                  type="button"
                  onClick={() => {
                    setWallet(selectedIds);
                    setOverride(null);
                  }}
                  className="mt-3 min-h-11 rounded-xl border border-gold/40 bg-gold/10 px-3.5 py-2 text-sm font-medium text-gold transition-colors hover:bg-gold/15 sm:min-h-0"
                >
                  Save these as my cards
                </button>
              ) : null}
              <div
                id="card-picker"
                className={`mt-4 ${pickerOpen ? "" : "hidden"} lg:block`}
              >
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

          <div aria-busy={pending}>
            <p className="sr-only" aria-live="polite">
              {pending
                ? "Working it out…"
                : result
                  ? `Answer ready for ₹${inr.format(result.amount_inr)}.`
                  : ""}
            </p>
            {error ? (
              <p className="rounded-xl border border-destructive/40 bg-destructive/5 px-4 py-3 text-sm text-destructive">
                {error}
              </p>
            ) : !ready && cards.length === 0 ? (
              <div className="flex justify-center py-16">
                <PlaneLoader />
              </div>
            ) : !ready ? (
              <EmptyState />
            ) : pending && !result ? (
              <div className="flex justify-center py-16">
                <PlaneLoader />
              </div>
            ) : result && shown ? (
              <div className={pending ? "opacity-60 transition-opacity" : "transition-opacity"}>
              <Result
                result={result}
                programId={programId}
                onSelectProgram={setProgramId}
                goalProgram={goalProgram}
                comparingAll={shown.comparingAll}
                closedCardIds={
                  new Set(cards.filter((c) => !c.acquirable).map((c) => c.id))
                }
              />
              </div>
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
        Enter an amount to see which card wins.
      </p>
    </div>
  );
}

type GoalProgram = { programId: string; goalName: string } | null;

/** The program of the signed-in user's most recent active goal, if any — a
 * program the USER chose, so it may lead the verdicts (CLAUDE.md: a target is
 * chosen by the user or inherited from a goal they set, never assumed). It
 * only reorders and labels; it never selects a program on the user's behalf. */
function useGoalProgram(): GoalProgram {
  const { user } = useAuth();
  const [goal, setGoal] = useState<GoalProgram>(null);
  useEffect(() => {
    if (!user) return;
    let active = true;
    getAccessToken()
      .then((token) => (token ? fetchSavedGoals(token) : []))
      .then((goals) => {
        const latest = goals.find((g) => g.status === "active" && g.partner_id);
        if (active && latest?.partner_id) {
          setGoal({ programId: latest.partner_id, goalName: latest.goal_name });
        }
      })
      // Signed-in extras are optional — a failed goals read changes nothing.
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [user]);
  return user ? goal : null;
}

const CATEGORY_NAMES = new Map(
  SPEND_CATEGORIES.map((c) => [c.slug, c.label.toLowerCase()] as const),
);

function unitOf(verdict: Pick<ProgramVerdict, "partner_type">): string {
  return verdict.partner_type === "hotel" ? "points" : "miles";
}

/** "1 mile", "2 miles" — `unit` is the plural form. */
function count(n: number, unit: string): string {
  return `${inr.format(n)} ${n === 1 ? unit.replace(/s$/, "") : unit}`;
}

/** "16.6500" → "16.65". Display only; the engine keeps the precision. */
function trimRate(value: string): string {
  const n = Number(value);
  return Number.isFinite(n) ? String(Number(n.toFixed(4))) : value;
}

function Result({
  result,
  programId,
  onSelectProgram,
  goalProgram,
  comparingAll,
  closedCardIds,
}: {
  result: BestCardResult;
  programId: string | null;
  onSelectProgram: (id: string | null) => void;
  goalProgram: GoalProgram;
  comparingAll: boolean;
  closedCardIds: Set<string>;
}) {
  const chooser = (
    <ProgramChooser
      reach={result.partner_reach}
      selectedId={programId}
      onSelect={onSelectProgram}
      prompt={programId ? "Sending these points to" : "See the full working for one program"}
      showBestRoute={false}
      clearLabel="Tap again to see every program."
      labelFor={(p) => programLabel(p)}
      hideCount
    />
  );

  // Drilling in or out swaps the whole view: bring its top into sight and
  // move focus there, or keyboard users are dropped at <body> and the page
  // is left scrolled deep into content that no longer exists.
  const topRef = useRef<HTMLDivElement>(null);
  const shownProgram = result.target_program_id;
  const previous = useRef(shownProgram);
  useEffect(() => {
    if (previous.current === shownProgram) return;
    previous.current = shownProgram;
    const node = topRef.current;
    if (!node) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    node.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
    node.focus({ preventScroll: true });
  }, [shownProgram]);

  const closed = comparingAll ? closedCardIds : new Set<string>();
  return (
    <div ref={topRef} tabIndex={-1} className="scroll-mt-24 space-y-6 outline-none">
      {comparingAll ? (
        <p className="rounded-xl border border-hairline px-4 py-3 text-sm text-muted-foreground">
          {`You haven't picked any cards, so this compares all ${result.ranked.length + result.unroutable.length} cards we cover. Pick the ones you hold to see only yours.`}
        </p>
      ) : null}
      {result.ranking_basis === "points" ? (
        <PointsFirst
          result={result}
          chooser={chooser}
          goalProgram={goalProgram}
          onSelectProgram={onSelectProgram}
          comparingAll={comparingAll}
          closed={closed}
        />
      ) : (
        <Priced result={result} chooser={chooser} onBack={() => onSelectProgram(null)} />
      )}
    </div>
  );
}

// ── Plain-language helpers ───────────────────────────────────────────────

type ProgramLike = { program_name: string; partner_name: string };
type UnitLike = ProgramLike & { partner_type: "airline" | "hotel" };

/** "KrisFlyer (Singapore Airlines)", "Accor Live Limitless", "Marriott Bonvoy". */
function programLabel(d: ProgramLike): string {
  const name = d.program_name.replace(/^ALL - /, "");
  const brand = d.partner_name.split(" ")[0] ?? "";
  return name.toLowerCase().includes(brand.toLowerCase())
    ? name
    : `${name} (${d.partner_name})`;
}

/** The program's own unit, named: "KrisFlyer miles", "Accor points". */
function unitName(d: UnitLike): string {
  if (d.partner_type === "airline") return `${d.program_name} miles`;
  return d.program_name.startsWith("ALL - ")
    ? `${d.partner_name} points`
    : `${d.program_name} points`;
}

/** "1,665 KrisFlyer miles", "1 KrisFlyer mile". */
function countIn(n: number, d: UnitLike): string {
  return count(n, unitName(d));
}

function isCashback(option: CardSpendOption): boolean {
  return /cashback/i.test(option.currency_name);
}

/** "HDFC Reward Points (Infinia/Diners tier)" → "HDFC Reward Points". */
function shortCurrency(option: CardSpendOption): string {
  return option.currency_name.replace(/\s*\(.*\)$/, "");
}

/** "1,665 HDFC Reward Points" or "₹100 cashback". */
function earnPhrase(option: CardSpendOption, points = option.points_earned): string {
  return isCashback(option)
    ? `₹${inr.format(points)} cashback`
    : `${inr.format(points)} ${shortCurrency(option)}`;
}

/** "16.65 HDFC Reward Points per ₹100" or "1% cashback". */
function ratePhrase(option: CardSpendOption): string {
  const rate = trimRate(option.effective_earn_rate);
  return isCashback(option)
    ? `${rate}% back`
    : `${rate} ${shortCurrency(option)} per ₹100`;
}

function cardName(option: { bank: string; card_name: string }): string {
  return `${option.bank} ${option.card_name}`;
}

function spendPhrase(result: BestCardResult): string {
  const amount = `₹${inr.format(result.amount_inr)}`;
  return result.category === "default"
    ? `${amount} of everyday spend`
    : `${amount} of ${CATEGORY_NAMES.get(result.category) ?? "this"}`;
}

function ClosedLabel({ show }: { show: boolean }) {
  if (!show) return null;
  return (
    <>
      {" "}
      <span className="text-xs font-normal text-muted-foreground">
        (not open to new applicants)
      </span>
    </>
  );
}

/** Programs grouped by the cards that top them — the card-first answer. */
type Group = { winners: CardSpendOption[]; verdicts: ProgramVerdict[] };

function groupByWinners(result: BestCardResult): {
  groups: Group[];
  nobody: ProgramVerdict[];
} {
  const byKey = new Map<string, Group>();
  const nobody: ProgramVerdict[] = [];
  for (const verdict of result.program_verdicts) {
    const winners = result.ranked.filter((o) => o.best_for.includes(verdict.program_id));
    if (verdict.winner === null || winners.length === 0) {
      nobody.push(verdict);
      continue;
    }
    const key = winners.map((o) => o.card_id).sort().join("|");
    const group = byKey.get(key) ?? { winners, verdicts: [] };
    group.verdicts.push(verdict);
    byKey.set(key, group);
  }
  return { groups: [...byKey.values()], nobody };
}

// ── Step 1: the answer, then the cards ──────────────────────────────────

/** Step 1 — card-first: one plain answer, then the other cards in order. */
function PointsFirst({
  result,
  chooser,
  goalProgram,
  onSelectProgram,
  comparingAll,
  closed,
}: {
  result: BestCardResult;
  chooser: React.ReactNode;
  goalProgram: GoalProgram;
  onSelectProgram: (id: string) => void;
  comparingAll: boolean;
  closed: Set<string>;
}) {
  const { groups, nobody } = groupByWinners(result);
  const single = result.ranked.length === 1 ? result.ranked[0] : null;
  const tooSmall =
    !result.no_card_earns &&
    result.ranked.every(
      (o) => o.points_earned === 0 && Number(o.effective_earn_rate) > 0,
    );

  // Which cards the answer panel already covers in full — the list below
  // shows the rest, so nothing is said twice.
  let answered: CardSpendOption[] = [];
  let panel: React.ReactNode;
  let showChooser = true;
  if (result.no_card_earns) {
    panel = (
      <NobodyEarns
        category={result.category}
        cardCount={result.ranked.length}
        comparingAll={comparingAll}
      />
    );
    showChooser = false;
  } else if (tooSmall) {
    panel = <TooSmall result={result} comparingAll={comparingAll} />;
    showChooser = false;
  } else if (single) {
    answered = [single];
    panel = <PickPanel result={result} picks={[single]} reason="only" closed={closed} />;
  } else if (groups.length === 1 && nobody.length === 0) {
    answered = groups[0].winners;
    panel = (
      <PickPanel
        result={result}
        picks={groups[0].winners}
        reason={groups[0].winners.length === 1 ? "everywhere" : "tie"}
        closed={closed}
        comparingAll={comparingAll}
      />
    );
  } else if (groups.length === 0) {
    panel = <NoTransfers result={result} />;
  } else {
    panel = (
      <DependsPanel
        result={result}
        groups={groups}
        nobody={nobody}
        goalProgram={goalProgram}
        onSelectProgram={onSelectProgram}
        closed={closed}
      />
    );
    showChooser = false; // the panel's program buttons are the drill-in
  }

  const rest = result.ranked.filter((o) => !answered.includes(o));
  const showList = rest.length > 0 && !result.no_card_earns && !tooSmall;

  return (
    <div className="space-y-8">
      {panel}

      {showList ? (
        <div>
          <h3 className="text-sm font-semibold text-foreground">
            {answered.length > 0
              ? "Your other cards, in order"
              : comparingAll
                ? "Every card, in order"
                : "Your cards, in order"}
          </h3>
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
            Ordered by how many programs each card is best for, then by how close
            it comes in the others. Points from different banks aren&apos;t the same
            unit, so we never rank by the raw number.
          </p>
          <ol className="mt-4 space-y-3">
            {rest.map((option) => (
              <CardBlock
                key={option.card_id}
                option={option}
                result={result}
                closed={closed.has(option.card_id)}
              />
            ))}
          </ol>
        </div>
      ) : null}

      {showChooser && result.partner_reach.length > 1 ? chooser : null}

      <Footnotes result={result} />
    </div>
  );
}

/** "Use X" — the only card, the card that wins everywhere, or a tie. */
function PickPanel({
  result,
  picks,
  reason,
  closed,
  comparingAll = false,
}: {
  result: BestCardResult;
  picks: CardSpendOption[];
  reason: "only" | "everywhere" | "tie";
  closed: Set<string>;
  comparingAll?: boolean;
}) {
  const lead = picks[0];
  const portal = picks.find((p) => p.requires_portal)?.requires_portal ?? null;
  const why =
    reason === "only"
      ? comparingAll
        ? "It's the only card we cover."
        : "It's the only card you've picked."
      : reason === "everywhere"
        ? comparingAll
          ? `Of the cards we cover, it earns the most in every program you could transfer to.`
          : "It earns the most in every program you could transfer to."
        : "They earn exactly the same here, in every program they can transfer to — use either.";

  return (
    <section className="rounded-2xl border border-gold/40 bg-gold/6 p-6">
      <p className="text-xs font-medium uppercase tracking-[0.14em] text-gold">
        The answer
      </p>
      <h2 className="mt-2 text-2xl font-semibold sm:text-3xl">
        Use {picks.map((p) => cardName(p)).join(" or ")}
        <Unverified flag={picks.some((p) => p.needs_verification)} />
        {portal ? (
          <span className="mt-1 block text-lg font-medium text-gold sm:text-xl">
            {`booked through ${portal}`}
          </span>
        ) : null}
      </h2>
      {picks.some((p) => closed.has(p.card_id)) ? (
        <p className="mt-1 text-xs text-muted-foreground">
          {`${picks.filter((p) => closed.has(p.card_id)).map((p) => p.card_name).join(" and ")} isn't open to new applicants.`}
        </p>
      ) : null}
      <p className="mt-2 text-base text-muted-foreground">{why}</p>

      <p className="mt-4 text-base">
        {`${spendPhrase(result)} earns `}
        <span className="font-semibold">{earnPhrase(lead)}</span>
        {`, at ${ratePhrase(lead)}${reason === "tie" ? " on each" : ""}.`}
      </p>
      {lead.requires_portal ? (
        <p className="mt-2 text-sm text-muted-foreground">
          {`That's only through ${lead.requires_portal}. Booked directly with the airline or hotel, ${reason === "tie" ? "each" : "it"} earns ${earnPhrase(lead, lead.direct_points_earned)} instead.`}
        </p>
      ) : null}
      <CapNote option={lead} />

      <Destinations option={lead} />

      {portal && reason !== "only" ? (
        <DirectAlternatives result={result} picks={picks} closed={closed} />
      ) : null}
    </section>
  );
}

/** Where a card's points can go, and what this spend becomes there. */
function Destinations({ option }: { option: CardSpendOption }) {
  const dests = option.destinations;
  if (dests.length === 0) {
    return (
      <p className="mt-4 text-sm text-muted-foreground">
        {isCashback(option)
          ? "It's cashback — it comes straight off your bill, so there's nothing to transfer."
          : `These points can't be transferred to an airline or hotel program; they're redeemed with ${option.bank}.`}
      </p>
    );
  }
  if (dests.length === 1) {
    const d = dests[0];
    return (
      <p className="mt-4 text-sm text-muted-foreground">
        {`${option.card_name}'s ${shortCurrency(option)} transfer to ${programLabel(d)} at ${d.ratio_from} to ${d.ratio_to}, so this spend becomes `}
        <span className="font-semibold text-foreground">{countIn(d.partner_units, d)}</span>
        <Unverified flag={d.needs_verification} />.
      </p>
    );
  }
  return (
    <div className="mt-4 text-sm text-muted-foreground">
      <p>{`Transfer them to any of ${dests.length} airline or hotel programs:`}</p>
      <ul className="mt-2 space-y-1">
        {dests.map((d) => (
          <li key={d.program_id} className="flex flex-wrap justify-between gap-x-4">
            <span className="text-foreground">{programLabel(d)}</span>
            <span className="tabular-nums">
              {countIn(d.partner_units, d)}
              <Unverified flag={d.needs_verification} />
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** When the pick's rate needs a portal: what to use when booking directly.
 * Never names the pick as its own alternative. */
function DirectAlternatives({
  result,
  picks,
  closed,
}: {
  result: BestCardResult;
  picks: CardSpendOption[];
  closed: Set<string>;
}) {
  const pickIds = new Set(picks.map((p) => p.card_id));
  const alternatives = result.program_verdicts.filter(
    (v) => v.direct_winner && !v.direct_tied,
  );
  const others = alternatives.filter((v) => !pickIds.has(v.direct_winner?.card_id ?? ""));
  if (alternatives.length === 0) return null;

  let body: React.ReactNode;
  if (others.length === 0) {
    body = (
      <p className="mt-1 text-muted-foreground">
        {`${picks.length === 1 ? picks[0].card_name : "These"} still ${picks.length === 1 ? "earns" : "earn"} the most, just at the base rate.`}
      </p>
    );
  } else {
    const ids = new Set(others.map((v) => v.direct_winner?.card_id));
    const one = others[0].direct_winner;
    if (
      ids.size === 1 &&
      one &&
      others.length === result.program_verdicts.length
    ) {
      body = (
        <p className="mt-1 text-muted-foreground">
          {`Use ${one.bank} ${one.card_name} instead — it earns the most in every program when the portal bonus doesn't apply.`}
          {closed.has(one.card_id) ? " (Not open to new applicants.)" : ""}
        </p>
      );
    } else {
      body = (
        <ul className="mt-1 space-y-0.5 text-muted-foreground">
          {alternatives.map((v) => {
            const d = v.direct_winner;
            if (!d) return null;
            return (
              <li key={v.program_id}>
                {pickIds.has(d.card_id)
                  ? `${programLabel(v)}: still ${d.card_name}, at the base rate — ${countIn(d.partner_units, v)}`
                  : `${programLabel(v)}: ${d.bank} ${d.card_name} — ${countIn(d.partner_units, v)}${closed.has(d.card_id) ? " (not open to new applicants)" : ""}`}
                <Unverified flag={d.needs_verification} />
              </li>
            );
          })}
        </ul>
      );
    }
  }
  return (
    <div className="mt-4 rounded-xl border border-hairline bg-background/40 px-4 py-3 text-sm">
      <p className="font-medium text-foreground">
        Booking directly with the airline or hotel instead?
      </p>
      {body}
    </div>
  );
}

/** No single answer: the best card changes with the program. Grouped by
 * card, so a card that wins several programs is said once. */
function DependsPanel({
  result,
  groups,
  nobody,
  goalProgram,
  onSelectProgram,
  closed,
}: {
  result: BestCardResult;
  groups: Group[];
  nobody: ProgramVerdict[];
  goalProgram: GoalProgram;
  onSelectProgram: (id: string) => void;
  closed: Set<string>;
}) {
  // The user's goal program's group first; then groups covering more
  // programs; airlines before hotels inside each. Nothing is privileged.
  const isGoal = (v: ProgramVerdict) => v.program_id === goalProgram?.programId;
  const ordered = [...groups]
    .map((g) => ({
      ...g,
      verdicts: [...g.verdicts].sort(
        (a, b) =>
          Number(isGoal(b)) - Number(isGoal(a)) ||
          Number(a.partner_type === "hotel") - Number(b.partner_type === "hotel") ||
          programLabel(a).localeCompare(programLabel(b)),
      ),
    }))
    .sort(
      (a, b) =>
        Number(b.verdicts.some(isGoal)) - Number(a.verdicts.some(isGoal)) ||
        b.verdicts.length - a.verdicts.length,
    );

  return (
    <section className="rounded-2xl border border-gold/40 bg-gold/6 p-6">
      <p className="text-xs font-medium uppercase tracking-[0.14em] text-gold">
        The answer
      </p>
      <h2 className="mt-2 text-xl font-semibold sm:text-2xl">
        The best card depends on where you send your points
      </h2>
      <p className="mt-2 text-sm text-muted-foreground">
        {`For ${spendPhrase(result)}, each card below is the best one for the programs listed under it. Tap a program for the full working.`}
      </p>
      <ul className="mt-5 space-y-5">
        {ordered.map((group) => {
          const portalCards = group.winners.filter((w) => w.requires_portal);
          return (
            <li key={group.winners.map((w) => w.card_id).join("|")}>
              <p className="text-[15px] font-semibold">
                {group.winners.length > 1 ? "Either " : ""}
                <span className="text-gold">
                  {group.winners.map((w) => cardName(w)).join(" or ")}
                </span>
                <Unverified flag={group.winners.some((w) => w.needs_verification)} />
                <ClosedLabel show={group.winners.some((w) => closed.has(w.card_id))} />
              </p>
              {portalCards.length > 0 ? (
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {`Booked through ${portalCards[0].requires_portal}`}
                </p>
              ) : null}
              <ul className="mt-2 space-y-1.5">
                {group.verdicts.map((v) => (
                  <li key={v.program_id}>
                    <button
                      type="button"
                      onClick={() => onSelectProgram(v.program_id)}
                      className="flex w-full items-center justify-between gap-3 rounded-xl border border-hairline bg-background/40 px-3.5 py-2.5 text-left text-sm transition-colors hover:border-gold/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold/60"
                    >
                      <span className="min-w-0">
                        <span className="block text-muted-foreground">
                          {`Sending points to ${programLabel(v)}${isGoal(v) ? " (your goal)" : ""}`}
                        </span>
                        <span className="block font-medium text-foreground">
                          {v.winner
                            ? `${countIn(v.winner.partner_units, v)}${group.winners.length > 1 ? " each" : ""}`
                            : ""}
                        </span>
                        {v.direct_winner && !v.direct_tied && v.winner?.requires_portal ? (
                          <span className="block text-xs text-muted-foreground">
                            {group.winners.some((w) => w.card_id === v.direct_winner?.card_id)
                              ? `Booked directly: still the best, at ${countIn(v.direct_winner.partner_units, v)}`
                              : `Booked directly instead: ${v.direct_winner.bank} ${v.direct_winner.card_name}, ${countIn(v.direct_winner.partner_units, v)}`}
                          </span>
                        ) : null}
                        <span className="sr-only"> — open the full working</span>
                      </span>
                      <ChevronRight className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                    </button>
                  </li>
                ))}
              </ul>
            </li>
          );
        })}
      </ul>
      {nobody.length > 0 ? (
        <p className="mt-4 text-sm text-muted-foreground">
          {`No card here earns anything in ${nobody.map((v) => programLabel(v)).join(" or ")} on this spend.`}
        </p>
      ) : null}
    </section>
  );
}

function TooSmall({
  result,
  comparingAll,
}: {
  result: BestCardResult;
  comparingAll: boolean;
}) {
  return (
    <section className="rounded-2xl border border-hairline p-6">
      <h2 className="text-base font-medium">
        {`₹${inr.format(result.amount_inr)} is too small to earn a whole point or mile on ${comparingAll ? "any card we cover" : result.ranked.length === 1 ? "your card" : "any of your cards"}.`}
      </h2>
      <p className="mt-2 text-sm text-muted-foreground">
        Earning rounds down on each purchase. Try the amount you&apos;ll actually
        spend.
      </p>
    </section>
  );
}

function NoTransfers({ result }: { result: BestCardResult }) {
  return (
    <section className="rounded-2xl border border-hairline p-6">
      <h2 className="text-base font-medium">
        None of these cards transfer to an airline or hotel program.
      </h2>
      <p className="mt-2 text-sm text-muted-foreground">
        {`Their rewards are cashback or redeemed with the bank, so they can't be compared in one unit. Here's what each earns on ${spendPhrase(result)}.`}
      </p>
    </section>
  );
}

/** One card, in plain words, for the list under the answer. */
function CardBlock({
  option,
  result,
  closed,
}: {
  option: CardSpendOption;
  result: BestCardResult;
  closed: boolean;
}) {
  const best = result.program_verdicts.filter((v) => option.best_for.includes(v.program_id));
  const bestText =
    best.length === 0
      ? null
      : best.length === result.program_verdicts.length && best.length > 1
        ? `Best for all ${best.length} programs it can reach`
        : `Best for ${listJoin(best.map((v) => programLabel(v)))}`;
  const zero = Number(option.effective_earn_rate) === 0;
  const position = option.order_position;
  return (
    <li className="rounded-2xl border border-hairline px-4 py-4">
      <div className="flex items-start gap-3">
        {position !== null ? (
          <span
            aria-hidden="true"
            className="mt-0.5 grid size-6 shrink-0 place-items-center rounded-full border border-hairline text-xs tabular-nums text-muted-foreground"
          >
            {position}
          </span>
        ) : null}
        <div className="min-w-0 flex-1">
          <p className="text-[15px] font-semibold">
            {position !== null ? <span className="sr-only">{`${position}. `}</span> : null}
            {cardName(option)}
            <Unverified flag={option.needs_verification} />
            <ClosedLabel show={closed} />
          </p>
          {bestText ? (
            <p className="mt-1 text-xs font-medium text-gold">{bestText}</p>
          ) : null}
          <p className="mt-2 text-sm">
            {zero ? (
              <span className="text-muted-foreground">
                {`Earns nothing on ${CATEGORY_NAMES.get(result.category) ?? "this"} — the issuer excludes it.`}
              </span>
            ) : option.points_earned === 0 ? (
              <span className="text-muted-foreground">
                {`Too small to earn anything at ${ratePhrase(option)}.`}
              </span>
            ) : (
              <>
                {"Earns "}
                <span className="font-semibold">{earnPhrase(option)}</span>
                <span className="text-muted-foreground">
                  {`, at ${ratePhrase(option)}`}
                  {option.is_accelerated && !option.requires_portal
                    ? ` (${option.category_label})`
                    : ""}
                </span>
              </>
            )}
          </p>
          {option.requires_portal ? (
            <p className="mt-1 text-xs text-muted-foreground">
              {`Only through ${option.requires_portal}. Booked directly: ${earnPhrase(option, option.direct_points_earned)}.`}
            </p>
          ) : null}
          <CapNote option={option} />
          {!zero && option.points_earned > 0 ? (
            option.destinations.length === 0 ? (
              <p className="mt-2 text-xs text-muted-foreground">
                {isCashback(option)
                  ? "Cashback — comes straight off your bill."
                  : `Can't be transferred — redeemed with ${option.bank}.`}
              </p>
            ) : (
              <ul className="mt-2 space-y-0.5 text-xs text-muted-foreground">
                {option.destinations.map((d) => (
                  <li key={d.program_id}>
                    {`→ ${countIn(d.partner_units, d)}`}
                    <Unverified flag={d.needs_verification} />
                  </li>
                ))}
              </ul>
            )
          ) : null}
        </div>
      </div>
    </li>
  );
}

function CapNote({ option }: { option: CardSpendOption }) {
  if (!option.monthly_cap_inr) return null;
  const cap = `₹${inr.format(option.monthly_cap_inr)}`;
  const text = option.cap_exceeded
    ? option.over_cap_earn === "nothing"
      ? `Past its ${cap}/month cap the rest earns nothing — already counted above.`
      : `Past its ${cap}/month bonus cap the rest earns the base rate — already counted above.`
    : option.is_accelerated
      ? `The bonus rate applies to the first ${cap} each month.`
      : `Earning stops after ${cap} each month.`;
  return <p className="mt-1 text-xs text-muted-foreground">{text}</p>;
}

function listJoin(items: string[]): string {
  if (items.length <= 1) return items.join("");
  return `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
}

/** Step 3 — one program chosen: the verdict, its working, and the rest. */
function Priced({
  result,
  chooser,
  onBack,
}: {
  result: BestCardResult;
  chooser: React.ReactNode;
  onBack: () => void;
}) {
  const verdict = result.program_verdicts.find((v) => v.is_target) ?? null;
  const unit = verdict ? unitOf(verdict) : "miles";
  const program = result.target_program_name ?? "this program";
  const winnerOption = verdict?.winner
    ? result.ranked.find((o) => o.card_id === verdict.winner?.card_id)
    : undefined;
  const runnerUp = verdict?.runner_up ?? null;

  // The teaching moment: a card that earns MORE points but FEWER miles.
  const pointsUpset =
    winnerOption && !verdict?.tied
      ? result.ranked.find((o) => o.points_earned > winnerOption.points_earned)
      : undefined;

  // Always reachable near the top — the chooser sits far below on mobile, and
  // after a wallet change it may have no chips left to clear the program with.
  const back = (
    <button
      type="button"
      onClick={onBack}
      className="inline-flex min-h-11 items-center gap-1.5 rounded-lg text-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold/60 sm:min-h-0"
    >
      <ArrowLeft className="size-4" aria-hidden="true" />
      All programs
    </button>
  );

  if (result.ranked.length === 0) {
    return (
      <div className="space-y-6">
        {back}
        <div className="rounded-2xl border border-hairline p-6">
          <p className="text-base font-medium">
            None of these cards transfer to {program}.
          </p>
          <p className="mt-2 text-sm text-muted-foreground">
            They still earn rewards — they just can&apos;t reach this program.
          </p>
          <UnroutableList options={result.unroutable} category={result.category} />
        </div>
        {chooser}
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {back}
      {verdict?.too_small ? (
        <div className="rounded-2xl border border-hairline p-6">
          <p className="text-base font-medium">
            ₹{inr.format(result.amount_inr)} is too small to earn a whole{" "}
            {program} {unit.replace(/s$/, "")} on any of your cards.
          </p>
          <p className="mt-2 text-sm text-muted-foreground">
            Earning rounds down per purchase. Try the amount you&apos;ll actually
            spend.
          </p>
        </div>
      ) : !verdict || !verdict.winner || !winnerOption ? (
        <NobodyEarns
          category={result.category}
          program={program}
          unit={unit}
          cardCount={result.ranked.length}
          hasUnroutable={result.unroutable.length > 0}
        />
      ) : verdict.tied && runnerUp ? (
        <div className="rounded-2xl border border-hairline p-6">
          <h2 className="text-xs font-medium uppercase tracking-[0.14em] text-gold">
            It&apos;s a tie
          </h2>
          <p className="mt-2 text-xl font-semibold sm:text-2xl">
            {verdict.winner.card_name} or {runnerUp.card_name}
            <Unverified
              flag={verdict.winner.needs_verification || runnerUp.needs_verification}
            />
          </p>
          <p className="mt-3 text-base text-muted-foreground">
            Both earn {count(verdict.winner.partner_units, `${program} ${unit}`)} on ₹
            {inr.format(result.amount_inr)} — use either.
          </p>
          {[verdict.winner, runnerUp].some((pick) => pick.requires_portal) ? (
            <ul className="mt-3 flex flex-wrap gap-2">
              {[verdict.winner, runnerUp]
                .filter((pick) => pick.requires_portal)
                .map((pick) => (
                  <li
                    key={pick.card_id}
                    className="rounded-full border border-gold/40 px-3 py-1 text-sm text-gold"
                  >
                    {pick.card_name}: book through {pick.requires_portal}
                  </li>
                ))}
            </ul>
          ) : null}
          <Maths
            option={winnerOption}
            amountInr={result.amount_inr}
            unit={unit}
            category={result.category}
            program={program}
          />
          <DirectBox
            verdict={verdict}
            winnerOption={winnerOption}
            unit={unit}
            portal={
              [verdict.winner, runnerUp].find((pick) => pick.requires_portal)
                ?.requires_portal ?? null
            }
          />
        </div>
      ) : (
        <div className="rounded-2xl border border-gold/40 bg-gold/6 p-6">
          <h2 className="text-xs font-medium uppercase tracking-[0.14em] text-gold">
            Use this one
          </h2>
          <p className="mt-2 text-2xl font-semibold sm:text-3xl">
            {winnerOption.bank} {winnerOption.card_name}
            <Unverified flag={winnerOption.needs_verification} />
          </p>
          {winnerOption.requires_portal ? (
            <p className="mt-3 inline-flex items-center gap-1.5 rounded-full border border-gold/40 px-3 py-1 text-sm text-gold">
              Book through {winnerOption.requires_portal}
            </p>
          ) : null}
          <p className="mt-3 text-base text-muted-foreground">
            Earns{" "}
            <span className="font-semibold text-foreground">
              {inr.format(winnerOption.points_earned)} {winnerOption.currency_name}
            </span>{" "}
            on ₹{inr.format(result.amount_inr)} —{" "}
            <span className="font-semibold text-gold">
              {count(verdict.winner.partner_units, `${program} ${unit}`)}
            </span>
            .
          </p>
          {runnerUp && verdict.lead !== null ? (
            <p className="mt-2 text-sm text-muted-foreground">
              {runnerUp.partner_units === 0
                ? `The only card here that earns on this — ${runnerUp.card_name} earns nothing.`
                : `That's ${count(verdict.lead, `${program} ${unit}`)} more than ${runnerUp.card_name}, which earns ${inr.format(runnerUp.partner_units)}.`}
            </p>
          ) : null}
          <Maths
            option={winnerOption}
            amountInr={result.amount_inr}
            unit={unit}
            category={result.category}
            program={program}
          />
          <DirectBox
            verdict={verdict}
            winnerOption={winnerOption}
            unit={unit}
            portal={winnerOption.requires_portal}
          />
        </div>
      )}

      {pointsUpset && winnerOption && pointsUpset.card_id !== winnerOption.card_id ? (
        <p className="rounded-xl border border-hairline bg-input/10 px-4 py-3 text-sm leading-relaxed text-muted-foreground">
          <span className="font-medium text-foreground">Worth knowing:</span>{" "}
          {pointsUpset.card_name} earns more points here (
          {inr.format(pointsUpset.points_earned)} vs{" "}
          {inr.format(winnerOption.points_earned)}) but fewer {program} {unit},
          because it transfers at a worse ratio. Points across banks aren&apos;t the
          same unit — {program} {unit} are.
        </p>
      ) : null}

      {result.ranked.length > 1 ? (
      <div>
        <h2 className="text-sm font-semibold text-foreground">Every card, side by side</h2>
        <ul className="mt-3 divide-y divide-hairline rounded-xl border border-hairline">
          {result.ranked.map((option) => (
            <li key={option.card_id} className="px-4 py-3">
              <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                <span className="text-[15px] font-medium">{option.card_name}</span>
                <span className="text-sm text-muted-foreground">
                  {inr.format(option.points_earned)} {option.currency_name} →{" "}
                  <span className="text-foreground tabular-nums">
                    {count(option.miles_earned ?? 0, `${program} ${unit}`)}
                  </span>
                  <Unverified flag={option.needs_verification} />
                </span>
              </div>
              <ReasonLine option={option} category={result.category} program={program} />
            </li>
          ))}
        </ul>
      </div>
      ) : null}

      <UnroutableList options={result.unroutable} category={result.category} />

      {/* Switching programs only means something with more than one to
          switch to; "← All programs" above already goes back. */}
      {result.partner_reach.length > 1 ? chooser : null}

      <Footnotes result={result} priced />
    </div>
  );
}

/** "Booking directly with the airline or hotel?" — owed whenever the top
 * figure (a win or a tie) depends on a portal. */
function DirectBox({
  verdict,
  winnerOption,
  unit,
  portal,
}: {
  verdict: ProgramVerdict;
  winnerOption: CardSpendOption;
  unit: string;
  portal: string | null;
}) {
  const direct = verdict.direct_winner;
  if (!direct || !portal) return null;
  return (
    <div className="mt-4 rounded-xl border border-hairline bg-background/40 px-4 py-3 text-sm">
      <p className="font-medium text-foreground">
        Booking directly with the airline or hotel, not through {portal}?
      </p>
      <p className="mt-1 text-muted-foreground">
        {verdict.direct_tied ? (
          <>It&apos;s a tie at {count(direct.partner_units, unit)} — any of the tied cards will do.</>
        ) : direct.card_id === winnerOption.card_id && !verdict.tied ? (
          <>
            {winnerOption.card_name} still wins, but at its base rate:{" "}
            {count(direct.partner_units, unit)}
            <Unverified flag={direct.needs_verification} />.
          </>
        ) : (
          <>
            Use <span className="font-medium text-foreground">{direct.card_name}</span> —{" "}
            {count(direct.partner_units, unit)}
            <Unverified flag={direct.needs_verification} />.
            {!verdict.tied && winnerOption.requires_portal
              ? ` ${winnerOption.card_name} would earn only ${count(winnerOption.direct_miles_earned ?? 0, unit)} off its portal.`
              : null}
          </>
        )}
      </p>
    </div>
  );
}

/** "Why" in one line: the rate and where it comes from, the portal it needs,
 * the transfer ratio, and the cap — every figure straight from the option. */
function ReasonLine({
  option,
  category,
  program,
}: {
  option: CardSpendOption;
  category: SpendCategorySlug;
  program?: string;
}) {
  if (Number(option.effective_earn_rate) === 0) {
    return (
      <p className="mt-1 text-xs text-muted-foreground">
        Earns nothing — the issuer excludes {CATEGORY_NAMES.get(category) ?? "this"} spend
        from rewards.
      </p>
    );
  }
  const parts: string[] = [];
  const rate = ratePhrase(option);
  if (option.is_accelerated) {
    parts.push(`${option.category_label}: ${rate}`);
  } else if (category === "default") {
    parts.push(rate);
  } else {
    parts.push(`${rate} — no ${CATEGORY_NAMES.get(category) ?? "category"} bonus on this card`);
  }
  if (option.requires_portal) {
    parts.push(
      `only through ${option.requires_portal} (booked directly: ${earnPhrase(option, option.direct_points_earned)})`,
    );
  }
  if (program && option.transfer_ratio_from && option.transfer_ratio_to) {
    parts.push(`transfers to ${program} at ${option.transfer_ratio_from} to ${option.transfer_ratio_to}`);
  }
  if (option.cap_exceeded && option.monthly_cap_inr) {
    parts.push(
      option.over_cap_earn === "nothing"
        ? `nothing past the ₹${inr.format(option.monthly_cap_inr)}/month cap`
        : `base rate past the ₹${inr.format(option.monthly_cap_inr)}/month cap`,
    );
  } else if (option.monthly_cap_inr) {
    // Only a rate above base is a "bonus"; a capped base-level rate (SBI's 1%
    // offline) simply stops earning at the cap.
    parts.push(
      option.is_accelerated
        ? `bonus up to ₹${inr.format(option.monthly_cap_inr)}/month`
        : option.over_cap_earn === "nothing"
          ? `earns on up to ₹${inr.format(option.monthly_cap_inr)}/month, nothing after`
          : `capped at ₹${inr.format(option.monthly_cap_inr)}/month`,
    );
  }
  return <p className="mt-1 text-xs text-muted-foreground">{parts.join(" · ")}</p>;
}

function NobodyEarns({
  category,
  program,
  unit,
  cardCount,
  hasUnroutable = false,
  comparingAll = false,
}: {
  category: SpendCategorySlug;
  program?: string;
  unit?: string;
  cardCount: number;
  hasUnroutable?: boolean;
  comparingAll?: boolean;
}) {
  const what = CATEGORY_NAMES.get(category) ?? "this";
  const one = cardCount === 1;
  // Program-scoped: only the cards that REACH the program earn nothing here;
  // cards without a route may well earn.
  if (program) {
    return (
      <div className="rounded-2xl border border-hairline p-6">
        <h2 className="text-base font-medium">
          {one
            ? `The card that reaches ${program} earns no ${unit} on ${what}.`
            : `None of the cards that reach ${program} earn ${unit} on ${what}.`}
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">
          {`${one ? "Its issuer excludes" : "Their issuers exclude"} ${what} spend from rewards.`}
          {hasUnroutable ? " Cards without a route to it are listed below — they may still earn." : ""}
        </p>
      </div>
    );
  }
  const who = comparingAll
    ? "None of the cards we cover earn"
    : one
      ? "Your card doesn't earn"
      : "None of your cards earn";
  return (
    <div className="rounded-2xl border border-hairline p-6">
      <h2 className="text-base font-medium">{`${who} rewards on ${what}.`}</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        {`${one && !comparingAll ? "Its issuer excludes" : "Their issuers exclude"} ${what} spend from rewards, so no card earns anything on it.`}
      </p>
    </div>
  );
}

function Unverified({ flag }: { flag: boolean | null }) {
  if (!flag) return null;
  return (
    // `relative`: contains the sr-only child so it can't widen the page.
    <span className="relative ml-0.5" title="Unverified">
      <span aria-hidden="true" className="text-gold/80">
        *
      </span>
      <span className="sr-only"> unverified</span>
    </span>
  );
}

function Footnotes({ result, priced = false }: { result: BestCardResult; priced?: boolean }) {
  const anyUnverified =
    result.ranked.some((o) => o.needs_verification) ||
    result.program_verdicts.some((v) => v.winner?.needs_verification);
  return (
    <div className="space-y-2 text-xs leading-relaxed text-muted-foreground">
      {anyUnverified ? (
        <p>
          <span aria-hidden="true" className="text-gold/80">
            *
          </span>{" "}
          Unverified — from a published source we haven&apos;t checked line by line
          yet. Treat that figure as indicative.
        </p>
      ) : null}
      {priced || result.ranked.some((o) => o.monthly_cap_inr) ? (
        <p>
          {priced
            ? "Figures are what this spend adds to your balance — you transfer in blocks later. "
            : ""}
          {result.ranked.some((o) => o.monthly_cap_inr)
            ? "Monthly bonus caps are assumed unused before this purchase."
            : ""}
        </p>
      ) : null}
    </div>
  );
}

function Maths({
  option,
  amountInr,
  unit = "miles",
  category,
  program,
}: {
  option: CardSpendOption;
  amountInr: number;
  unit?: string;
  category?: SpendCategorySlug;
  program?: string;
}) {
  // "All other spend" on a dining purchase reads as a mistake: say it's the
  // card's base rate and that dining has no bonus on this card.
  const what = category ? (CATEGORY_NAMES.get(category) ?? "this") : "this";
  const rateName = option.is_accelerated
    ? option.category_label
    : category && category !== "default"
      ? `Base rate (no ${what} bonus on this card)`
      : "Base rate";
  const converted =
    option.transfer_ratio_from && option.transfer_ratio_to
      ? ` → at ${option.transfer_ratio_from} to ${option.transfer_ratio_to} = ${count(option.miles_earned ?? 0, program ? `${program} ${unit}` : unit)}`
      : "";
  return (
    <div className="mt-5 border-t border-gold/20 pt-4 text-sm text-muted-foreground">
      <p className="text-xs font-medium uppercase tracking-[0.12em]">The working</p>
      <p className="mt-1">
        <span className="text-foreground">{rateName}</span>
        {`: ₹${inr.format(amountInr)} × ${ratePhrase(option)} = ${earnPhrase(option)}${converted}`}
      </p>
      {option.cap_exceeded && option.monthly_cap_inr ? (
        <p className="mt-2 text-amber-300/90">
          This is above the ₹{inr.format(option.monthly_cap_inr)}/month bonus cap.{" "}
          {option.over_cap_earn === "nothing"
            ? "Spend past the cap earns nothing on this card, so the rate shown is already averaged down to account for it."
            : "Spend past the cap earns the base rate, so the rate shown is already blended down to account for it."}
        </p>
      ) : option.monthly_cap_inr ? (
        <p className="mt-2">
          {option.is_accelerated
            ? `Bonus rate applies up to ₹${inr.format(option.monthly_cap_inr)}/month.`
            : `Earning is capped at ₹${inr.format(option.monthly_cap_inr)}/month.`}
        </p>
      ) : null}
    </div>
  );
}

function UnroutableList({
  options,
  category,
}: {
  options: CardSpendOption[];
  category: SpendCategorySlug;
}) {
  if (options.length === 0) return null;
  return (
    <div>
      <p className="text-sm font-semibold text-foreground">No route to this program</p>
      <ul className="mt-3 divide-y divide-hairline rounded-xl border border-hairline">
        {options.map((option) => (
          <li key={option.card_id} className="px-4 py-3">
            <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
              <span className="text-[15px] font-medium">{option.card_name}</span>
              <span className="text-sm text-muted-foreground">
                {inr.format(option.points_earned)} {option.currency_name}
              </span>
            </div>
            <ReasonLine option={option} category={category} />
          </li>
        ))}
      </ul>
    </div>
  );
}
