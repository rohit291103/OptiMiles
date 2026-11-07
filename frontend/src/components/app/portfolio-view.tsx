"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Armchair,
  Check,
  CheckCircle2,
  CreditCard,
  Landmark,
  Pencil,
  Plane,
  Trash2,
  Trophy,
} from "lucide-react";

import { CardPicker } from "@/components/ui/card-picker";
import { ProgramChooser } from "@/components/ui/program-chooser";
import { getAccessToken } from "@/lib/supabase";
import { useAuth } from "@/lib/use-auth";
import { useWallet } from "@/lib/wallet";
import {
  ApiError,
  SPEND_CATEGORIES,
  fetchActivitySummary,
  fetchPortfolio,
  type ActivitySummary,
  type CapUse,
  type CardSummary,
  type MilestoneProgress,
  type PortfolioCard,
  type PortfolioCategory,
  type PortfolioEarnRule,
  type PortfolioLoungeAccess,
  type WalletPortfolio,
} from "@/lib/api";

const inr = new Intl.NumberFormat("en-IN");

/**
 * Portfolio View — `/cards` as the user's own wallet (roadmap Phase 1).
 *
 * The page leads with what the catalog states directly — earn rates, caps,
 * milestones, fees, and where each card CAN send points. Nothing is priced in
 * a transfer program until the user picks one, because points across issuers
 * are different units (HDFC RP, EDGE Miles, MR) and the catalog carries no
 * ₹-per-point valuation to convert them. Naming a winner before that choice
 * would be a guess dressed as an answer — see `CLAUDE.md` → *Never Assume the
 * User's Goal*. Once a program is chosen, everything reprices into it, and a
 * card that can't reach it reads "no route", never a zero.
 *
 * PROGRESS IS COMPOSED HERE, NOT IN `/v1/portfolio`. That endpoint is
 * anonymous, cacheable and catalog-only; cap utilisation and milestone
 * progress come from the signed-in user's activity log via
 * `/v1/activity/summary`, joined on (card, category) for caps and on
 * `milestone_id` for milestones. Without a session (or before anything is
 * logged) the page keeps the "targets, not progress" line. Every logged figure
 * is a LOWER bound — a milestone is "past the threshold on your log", never
 * "missed"; headroom is "at most" — and the window is the calendar, which the
 * copy says may differ from the statement cycle.
 *
 * Rows seeded from `needs_verification` data carry an "Unverified" label
 * (CLAUDE.md → tiered coverage). The caveat lines come from the API rather
 * than being written here, so the honesty lives with the numbers.
 */

/** What the activity log can add to this wallet. `key` is the signed-in user
 *  AND the wallet it was fetched for, so a result for another wallet — or,
 *  on a shared device, another person — is never shown. */
type ProgressResult =
  | { key: string; kind: "ready"; summary: ActivitySummary }
  | { key: string; kind: "anonymous" }
  | { key: string; kind: "expired" }
  | { key: string; kind: "error"; message: string };

/** null while the log is still being checked. */
type Progress = ProgressResult | null;
export function PortfolioView({ catalog }: { catalog: CardSummary[] }) {
  const { cardIds, setWallet, toggleCard, hydrated } = useWallet();
  const [portfolio, setPortfolio] = useState<WalletPortfolio | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  // null = no program chosen. The default, and a legitimate state.
  const [programId, setProgramId] = useState<string | null>(null);
  const [progressResult, setProgressResult] = useState<ProgressResult | null>(
    null,
  );
  // Bumped by "Try again" so the summary effect refetches.
  const [progressAttempt, setProgressAttempt] = useState(0);
  // Live session identity (subscribes to Supabase auth changes), so a
  // sign-out or account switch drops the previous person's progress at once.
  const { user, loading: authLoading } = useAuth();
  const userId = user?.id ?? null;

  // A card id the catalog no longer lists can't be un-picked (the picker only
  // renders cards that exist), so a stale wallet would 404 forever with no way
  // out. Split it off, price the rest, and offer an explicit removal — the
  // engine still fails loudly on an unknown id; this just stops the UI from
  // being a trap.
  const known = useMemo(
    () => cardIds.filter((id) => catalog.some((card) => card.id === id)),
    [cardIds, catalog],
  );
  const strayCount = catalog.length > 0 ? cardIds.length - known.length : 0;

  // No setState in the effect body (React lints it, and it cascades renders):
  // the empty wallet is handled by `empty` below, which never renders a
  // portfolio, so a stale result can't be shown after the wallet is cleared.
  useEffect(() => {
    if (!hydrated || known.length === 0) return;
    let cancelled = false;
    fetchPortfolio({ cardIds: known, targetProgramId: programId ?? undefined })
      .then((body) => {
        if (!cancelled) {
          setPortfolio(body);
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setPortfolio(null);
          setError(
            err instanceof ApiError
              ? err.message
              : "Couldn't load your portfolio.",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [hydrated, known, programId]);

  // The log is independent of the chosen programme (it is spend in rupees),
  // so it is fetched per (user, wallet), not per programme. Signed out — or
  // with auth unconfigured — there is no log, and the page says targets, not
  // progress, without a network round trip.
  const progressKey = `${userId ?? "anonymous"}|${known.join(",")}`;
  useEffect(() => {
    if (!hydrated || authLoading || known.length === 0 || userId === null)
      return;
    let cancelled = false;
    const key = `${userId}|${known.join(",")}`;
    void (async () => {
      try {
        const token = await getAccessToken();
        if (cancelled) return;
        if (!token) {
          setProgressResult({ key, kind: "expired" });
          return;
        }
        const summary = await fetchActivitySummary(known, token);
        if (!cancelled) setProgressResult({ key, kind: "ready", summary });
      } catch (err) {
        if (cancelled) return;
        setProgressResult(
          err instanceof ApiError && err.status === 401
            ? { key, kind: "expired" }
            : {
                key,
                kind: "error",
                message:
                  err instanceof ApiError
                    ? err.message
                    : "Couldn't load your log.",
              },
        );
      }
    })();
    return () => {
      cancelled = true;
      // Drop the previous result from memory, not just from the screen, the
      // moment the user or wallet changes (shared-device privacy).
      setProgressResult(null);
    };
  }, [hydrated, authLoading, known, userId, progressAttempt]);
  const retryProgress = useCallback(
    () => setProgressAttempt((attempt) => attempt + 1),
    [],
  );
  const progress: Progress =
    !authLoading && userId === null
      ? { key: progressKey, kind: "anonymous" }
      : progressResult?.key === progressKey
        ? progressResult
        : null;

  const empty = hydrated && known.length === 0;
  const loading = !empty && hydrated && portfolio === null && error === null;

  return (
    <div className="space-y-10">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-2xl">
          <h2 className="font-heading text-xl text-foreground sm:text-2xl">
            Your portfolio
          </h2>
          <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
            {empty
              ? "Tell us which cards you hold and we'll show you what they're actually worth — earn rates priced in miles, the caps that bite, and every milestone you could be leaving on the table."
              : "What your cards earn, what they unlock, and where those points can go. Pick a transfer programme below and we'll reprice the whole wallet in it."}
          </p>
        </div>
        {!empty && cardIds.length > 0 ? (
          <button
            type="button"
            onClick={() => setEditing((open) => !open)}
            className="flex min-h-11 shrink-0 items-center gap-2 rounded-xl border border-hairline px-3.5 py-2 text-sm font-medium text-muted-foreground transition-colors hover:border-white/25 hover:text-foreground sm:min-h-0"
          >
            {editing ? (
              <Check className="size-4" />
            ) : (
              <Pencil className="size-4" />
            )}
            {editing ? "Done" : "Edit wallet"}
          </button>
        ) : null}
      </header>

      {strayCount > 0 ? (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-destructive/40 bg-destructive/5 px-4 py-3">
          <p className="text-sm text-destructive">
            {strayCount === 1 ? "One card" : `${strayCount} cards`} in your
            wallet {strayCount === 1 ? "is" : "are"} no longer in the catalog,
            so {strayCount === 1 ? "it isn't" : "they aren't"} included below.
          </p>
          <button
            type="button"
            onClick={() => setWallet(known)}
            className="min-h-11 shrink-0 rounded-lg border border-destructive/40 px-3 py-1.5 text-sm font-medium text-destructive transition-colors hover:bg-destructive/10 sm:min-h-0"
          >
            Remove {strayCount === 1 ? "it" : "them"}
          </button>
        </div>
      ) : null}

      {error ? (
        <p className="rounded-xl border border-destructive/40 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          {error}
        </p>
      ) : null}

      {/* The picker is also the recovery path for a stale wallet, so an error
          opens it rather than telling the user to "edit" with nothing to
          edit. */}
      {(empty || editing || error !== null) && catalog.length > 0 ? (
        <section className="rounded-2xl border border-hairline bg-input/[0.07] p-5 sm:p-6">
          <p className="text-sm font-semibold text-foreground">
            Cards you hold
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            Saved on this device only — no account needed, and nothing about
            your spending leaves the browser.
          </p>
          <div className="mt-5">
            <CardPicker
              cards={catalog}
              selectedIds={[...cardIds]}
              onToggle={toggleCard}
            />
          </div>
          {cardIds.length > 0 ? (
            <button
              type="button"
              onClick={() => setWallet([])}
              className="mt-5 flex min-h-11 items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-destructive sm:min-h-0"
            >
              <Trash2 className="size-4" /> Clear my wallet
            </button>
          ) : null}
        </section>
      ) : null}

      {loading ? (
        <p className="text-sm text-muted-foreground" role="status">
          Pricing your wallet…
        </p>
      ) : null}

      {portfolio && !empty ? (
        <Portfolio
          portfolio={portfolio}
          progress={progress}
          onRetryProgress={retryProgress}
          programId={programId}
          onSelectProgram={setProgramId}
        />
      ) : null}
    </div>
  );
}

function Portfolio({
  portfolio,
  progress,
  onRetryProgress,
  programId,
  onSelectProgram,
}: {
  portfolio: WalletPortfolio;
  progress: Progress;
  onRetryProgress: () => void;
  programId: string | null;
  onSelectProgram: (id: string | null) => void;
}) {
  // Progress renders only once something is logged: "₹0 of ₹1,50,000" on
  // every cap of a user who has never opened the log is noise, not a floor.
  const summary =
    progress?.kind === "ready" && progress.summary.logged_spend_total_inr > 0
      ? progress.summary
      : null;
  const anyUnverified =
    portfolio.partner_reach.some(
      (reach) => reach.needs_verification === true,
    ) ||
    portfolio.cards.some(
      (card) =>
        card.needs_verification ||
        card.earn_rules.some((rule) => rule.needs_verification) ||
        card.milestones.some((milestone) => milestone.needs_verification) ||
        card.transfer_links.some((link) => link.needs_verification) ||
        card.lounge_access.some((access) => access.needs_verification === true),
    );

  return (
    <div className="space-y-10">
      <Summary portfolio={portfolio} />
      {/* The honesty line belongs where the numbers are first read, not only
          in the fine print 11,000px below. The full sentence still closes the
          page. */}
      <div className="-mt-6 space-y-1.5">
        <ProgressNote progress={progress} onRetry={onRetryProgress} />
        {anyUnverified ? (
          <p className="text-xs leading-relaxed text-muted-foreground/80">
            Rows marked <Unverified /> come from published sources we
            haven&apos;t yet checked line by line against the issuer — treat
            them as indicative and confirm before relying on them.
          </p>
        ) : null}
      </div>
      <ProgramChooser
        reach={portfolio.partner_reach}
        selectedId={programId}
        onSelect={onSelectProgram}
        prompt={
          programId
            ? "Priced for transfers to"
            : "Where would you send these points?"
        }
      />
      <CategoryTable
        categories={portfolio.categories}
        cards={portfolio.cards}
        programName={portfolio.target_program_name}
      />
      <section>
        <SectionHeading icon={CreditCard}>Card by card</SectionHeading>
        <div className="mt-4 space-y-4">
          {portfolio.cards.map((card) => (
            <CardPanel
              key={card.card_id}
              card={card}
              programName={portfolio.target_program_name}
              summary={summary}
            />
          ))}
        </div>
      </section>
      <LoungeAccessSection portfolio={portfolio} />
      <PartnerReach portfolio={portfolio} />
      {/* Once logged progress is on the page, the catalog-only caveat ("no
          record of your spend") is no longer the true one. The activity API's
          own caveat talks about lounge visits, which this page does not
          count, so the lower bound is restated in this page's terms. */}
      <p className="text-xs leading-relaxed text-muted-foreground/80">
        {summary
          ? "Cap and milestone progress comes from the spend you have logged, so it is a floor, not a record: anything you did not log is not counted. Treat amounts used as “at least this much” and room left as “at most this much”, and confirm with your issuer before relying on a cap or milestone."
          : portfolio.caveat}
      </p>
    </div>
  );
}

const NOTE_LINK =
  "inline-flex min-h-11 items-center text-xs text-muted-foreground underline underline-offset-4 hover:text-foreground sm:mt-1 sm:min-h-0";

function ProgressNote({
  progress,
  onRetry,
}: {
  progress: Progress;
  onRetry: () => void;
}) {
  // Its own line, not inline in the sentence: the 44px mobile tap target
  // would otherwise push the paragraph's lines apart.
  const logLink = (
    <Link href="/activity" className={NOTE_LINK}>
      Log spend
    </Link>
  );

  if (progress === null) {
    return (
      <p className="text-xs text-muted-foreground/80" role="status">
        Checking your log for progress…
      </p>
    );
  }
  if (
    progress.kind === "ready" &&
    progress.summary.logged_spend_total_inr > 0
  ) {
    const since = progress.summary.earliest_entry_on;
    return (
      <div>
        <p className="text-xs leading-relaxed text-muted-foreground/80">
          Progress below comes from{" "}
          <span className="text-muted-foreground">what you have logged</span>,
          so it is a floor: anything you didn&apos;t log isn&apos;t counted
          {since ? `, and nothing before ${formatDate(since)} is` : ""}. Caps
          and milestones are counted on calendar periods, which may differ from
          your statement cycle.
        </p>
        {logLink}
      </div>
    );
  }
  if (progress.kind === "ready") {
    return (
      <div>
        <p className="text-xs leading-relaxed text-muted-foreground/80">
          Nothing logged on these cards yet, so caps and milestones below are{" "}
          <span className="text-muted-foreground">targets, not progress</span>.
        </p>
        {logLink}
      </div>
    );
  }
  if (progress.kind === "expired") {
    return (
      <div>
        <p className="text-xs leading-relaxed text-muted-foreground/80">
          Your session has expired, so caps and milestones below are{" "}
          <span className="text-muted-foreground">targets, not progress</span>.
        </p>
        <Link href="/login" className={NOTE_LINK}>
          Sign in again to see your progress
        </Link>
      </div>
    );
  }
  if (progress.kind === "error") {
    return (
      <div>
        <p className="text-xs leading-relaxed text-muted-foreground/80">
          We couldn&apos;t load your log, so caps and milestones below are{" "}
          <span className="text-muted-foreground">targets, not progress</span>.{" "}
          {progress.message}
        </p>
        <div className="flex flex-wrap gap-x-4">
          <button type="button" onClick={onRetry} className={NOTE_LINK}>
            Try again
          </button>
          <Link href="/activity" className={NOTE_LINK}>
            Open my log
          </Link>
        </div>
      </div>
    );
  }
  return (
    <div>
      <p className="text-xs leading-relaxed text-muted-foreground/80">
        No spend data yet, so caps and milestones below are{" "}
        <span className="text-muted-foreground">targets, not progress</span>.
      </p>
      <Link href="/login" className={NOTE_LINK}>
        Sign in to see progress from your log
      </Link>
    </div>
  );
}

function Summary({ portfolio }: { portfolio: WalletPortfolio }) {
  const bestDoor = portfolio.partner_reach.find((reach) => reach.is_target);
  const programme = portfolio.target_program_name;
  return (
    <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <Stat label="Cards" value={String(portfolio.cards.length)} />
      <Stat
        label="Annual fees"
        value={`₹${inr.format(portfolio.total_annual_fees_inr)}`}
      />
      {/* With no programme chosen these two tiles would have to invent one to
          say anything, so they answer the question that IS well-posed: how
          many places can this wallet send points at all. */}
      <Stat
        label={programme ? `Reach ${programme}` : "Programmes reachable"}
        value={
          programme
            ? `${portfolio.cards_reaching_target} of ${portfolio.cards.length}`
            : String(portfolio.partner_reach.length)
        }
      />
      <Stat
        label={programme ? "Best transfer rate" : "Transferable cards"}
        value={
          programme
            ? bestDoor
              ? `${inr.format(bestDoor.best_miles_per_1000_points)} mi / 1,000 pts`
              : "No route"
            : `${portfolio.cards.filter((card) => card.transfer_links.length > 0).length} of ${portfolio.cards.length}`
        }
      />
    </dl>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-hairline bg-input/[0.07] px-4 py-3">
      <dt className="text-xs sm:text-[11px] uppercase tracking-[0.12em] text-muted-foreground">
        {label}
      </dt>
      <dd className="mt-1 font-heading text-lg tabular-nums text-foreground">
        {value}
      </dd>
    </div>
  );
}

/**
 * The actionable summary: which card wins each category, and by how much.
 *
 * Cards without an accelerated rule still appear at their base rate — the
 * same fallback the engine applies — because "is my travel card actually
 * better here?" is the question this table exists to answer.
 */
function CategoryTable({
  categories,
  cards,
  programName,
}: {
  categories: PortfolioCategory[];
  cards: PortfolioCard[];
  programName: string | null;
}) {
  const names = useMemo(
    () => new Map(cards.map((card) => [card.card_id, card.card_name])),
    [cards],
  );

  // A stable callback ref, so React invokes it on mount (and on unmount with
  // null) rather than on every render — measuring in an effect would be a
  // setState-in-effect cascade.
  const [scroll, setScroll] = useState({ overflowing: false, atEnd: true });
  const measure = useCallback((element: HTMLDivElement | null) => {
    if (!element) return;
    setScroll({
      overflowing: element.scrollWidth > element.clientWidth + 1,
      atEnd:
        element.scrollLeft + element.clientWidth >= element.scrollWidth - 1,
    });
  }, []);

  return (
    <section>
      <SectionHeading icon={Trophy}>
        {programName
          ? "Which card wins, by category"
          : "What each card earns, by category"}
      </SectionHeading>
      <p className="mt-1.5 text-sm text-muted-foreground">
        {programName ? (
          <>
            {programName} miles per ₹100 spent. Higher is better — and it is not
            always the card earning the most points.
          </>
        ) : (
          <>
            Points per ₹100 spent, each in its own currency —{" "}
            <span className="text-foreground">
              so these columns aren&apos;t comparable to each other yet
            </span>
            . Pick a transfer programme above and we&apos;ll say which card
            actually wins.
          </>
        )}
      </p>
      {/* The row header stays pinned while the card columns scroll: without
          it, scrolling right on a wide wallet leaves bare numbers with no
          category to attach them to. The right-edge fade is the only signal
          that there is more table — a plain bordered box reads as complete,
          and on a phone a 9-card wallet shows about a quarter of itself. */}
      <div className="relative mt-4">
        <div
          ref={measure}
          onScroll={(event) => measure(event.currentTarget)}
          className="overflow-x-auto rounded-2xl border border-hairline"
        >
          <table className="w-full min-w-[34rem] border-collapse text-sm">
            <thead>
              <tr className="border-b border-hairline text-left">
                <th
                  scope="col"
                  className="sticky left-0 z-20 bg-background px-4 py-3 font-medium text-muted-foreground"
                >
                  Category
                </th>
                {cards.map((card) => (
                  <th
                    key={card.card_id}
                    scope="col"
                    className="whitespace-nowrap px-4 py-3 text-right font-medium text-muted-foreground"
                  >
                    {card.card_name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {categories.map((category) => (
                <tr
                  key={category.category_slug}
                  className="border-b border-hairline/60 last:border-0"
                >
                  <th
                    scope="row"
                    className="sticky left-0 z-10 bg-background px-4 py-3 text-left font-medium text-foreground"
                  >
                    {/* The canonical category name, not the winning card's own
                      label — a row headed "Online spend (5% cashback)" reads
                      as one issuer's framing of a shared category. The
                      card-specific label still shows in that card's panel,
                      where it is the useful detail. */}
                    {categoryLabel(category)}
                    {category.leader_withheld_unverified ? (
                      <span className="block text-xs font-normal text-muted-foreground">
                        No verified leader
                      </span>
                    ) : category.no_card_earns ||
                      category.rows.every((r) => Number(r.earn_rate) === 0) ? (
                      // The engine flags this only with a programme chosen;
                      // the every-row check covers the points view too.
                      <span className="block text-xs font-normal text-muted-foreground">
                        None of your cards earn here
                      </span>
                    ) : null}
                  </th>
                  {cards.map((card) => {
                    const row = category.rows.find(
                      (r) => r.card_id === card.card_id,
                    );
                    const leads = category.leader_card_id === card.card_id;
                    return (
                      <td
                        key={card.card_id}
                        className={`whitespace-nowrap px-4 py-3 text-right tabular-nums ${
                          leads
                            ? "font-semibold text-gold"
                            : "text-muted-foreground"
                        }`}
                      >
                        {/* With a programme chosen the cell is that
                            programme's miles, and a card with no route to it
                            is honestly blank. With none chosen the cell is the
                            card's own points rate — real, useful, and NOT
                            comparable sideways, which the subtitle says. */}
                        {row && Number(row.earn_rate) === 0 ? (
                          // An issuer exclusion: say so on hover and to
                          // screen readers, and read weaker than a real rate
                          // so it can't be mistaken for the dash (no route).
                          <span
                            className="relative text-muted-foreground/60"
                            title="This card's issuer excludes this spend from rewards"
                          >
                            0
                            <span className="sr-only"> — excluded by the issuer</span>
                          </span>
                        ) : (programName ? row?.miles_per_100 : row?.earn_rate) ? (
                          <>
                            {trimRate(
                              (programName
                                ? row?.miles_per_100
                                : row?.earn_rate) as string,
                            )}
                            {/* "base" only earns its place where an accelerated
                              rate was possible — on the catch-all row every
                              card is on its base rate by definition. */}
                            {/* A 0 is an issuer exclusion, not a base rate —
                              labelling it "base" would say the opposite. */}
                            {row?.is_accelerated ||
                            category.category_slug === "default" ||
                            Number(row?.earn_rate) === 0 ? null : (
                              <span className="ml-1 text-xs sm:text-[11px] text-muted-foreground/70">
                                base
                              </span>
                            )}
                            {row?.needs_verification ? (
                              // `relative` makes this span the sr-only
                              // child's containing block; without it the
                              // absolutely positioned text escapes the
                              // scroller and widens the whole page on mobile.
                              <span
                                className="relative ml-0.5"
                                title="Unverified"
                              >
                                <span
                                  aria-hidden="true"
                                  className="text-gold/80"
                                >
                                  *
                                </span>
                                <span className="sr-only"> unverified</span>
                              </span>
                            ) : null}
                          </>
                        ) : (
                          <span
                            title={
                              programName
                                ? `No transfer route to ${programName}`
                                : undefined
                            }
                          >
                            —
                          </span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {scroll.overflowing && !scroll.atEnd ? (
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-y-px right-px w-16 rounded-r-2xl bg-gradient-to-l from-background to-transparent"
          />
        ) : null}
      </div>
      {scroll.overflowing ? (
        <p className="mt-2 text-xs text-muted-foreground/80">
          Scroll the table sideways to compare all {cards.length} cards.
        </p>
      ) : null}
      {categories.some((c) => c.rows.some((r) => r.needs_verification)) ? (
        <p className="mt-2 text-xs text-muted-foreground/80">
          <span aria-hidden="true" className="text-gold/80">
            *
          </span>{" "}
          Unverified rate — from a published source we haven&apos;t checked line
          by line yet.
        </p>
      ) : null}
      {categories.some((c) => c.leader_withheld_unverified) ? (
        <p className="mt-2 text-xs leading-relaxed text-muted-foreground/80">
          &ldquo;No verified leader&rdquo; means the card that would come out on
          top in that category does so on a figure we haven&apos;t verified yet
          — so we don&apos;t name a winner rather than recommend on it.
        </p>
      ) : null}
      {categories.some((c) =>
        c.rows.some((r) => Number(r.earn_rate) === 0),
      ) ? (
        <p className="mt-2 text-xs text-muted-foreground/80">
          A 0 means that card&apos;s issuer excludes the spend from rewards —
          fuel and utilities, most often.
        </p>
      ) : null}
      {/* Derived from the cells themselves: a dash is any row with no miles
          figure that is not a 0-rate exclusion. Leader fields were a proxy
          that could hide this note while dashes were still on screen. */}
      {programName &&
      categories.some((c) =>
        c.rows.some(
          (r) => r.miles_per_100 === null && Number(r.earn_rate) !== 0,
        ),
      ) ? (
        <p className="mt-2 text-xs text-muted-foreground/80">
          A dash means that card has no transfer route to {programName} — it
          still earns rewards, they just can&apos;t reach this program.
        </p>
      ) : null}
      <p className="sr-only">
        {categories
          .filter((category) => category.leader_card_id)
          .map(
            (category) =>
              `${category.category_label}: use ${names.get(category.leader_card_id ?? "") ?? ""}.`,
          )
          .join(" ")}
      </p>
    </section>
  );
}

function CardPanel({
  card,
  programName,
  summary,
}: {
  card: PortfolioCard;
  programName: string | null;
  /** The activity summary, or null when there is no logged progress to show. */
  summary: ActivitySummary | null;
}) {
  const caps = summary
    ? summary.caps.filter((cap) => cap.card_id === card.card_id)
    : [];
  const milestoneProgress = new Map(
    (summary?.milestones ?? [])
      .filter((m) => m.card_id === card.card_id)
      .map((m) => [m.milestone_id, m] as const),
  );

  return (
    <article className="rounded-2xl border border-hairline bg-input/[0.05] p-5 sm:p-6">
      <header className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <div>
          <h4 className="flex flex-wrap items-center gap-x-2 gap-y-1 font-heading text-base text-foreground sm:text-lg">
            {card.bank} {card.card_name}
            {card.needs_verification ? <Unverified /> : null}
          </h4>
          <p className="mt-1 text-xs text-muted-foreground">
            Earns {card.currency_name}
            {card.currency_expiry_rules
              ? ` · ${card.currency_expiry_rules}`
              : ""}
            {card.has_lounge_access ? " · Lounge access" : ""}
          </p>
        </div>
        <p className="text-sm tabular-nums text-muted-foreground">
          {card.annual_fee_inr === 0
            ? "No annual fee"
            : `₹${inr.format(card.annual_fee_inr)}/yr`}
        </p>
      </header>

      {card.reaches_target === false ? (
        <p className="mt-4 rounded-xl border border-hairline bg-background/40 px-3.5 py-2.5 text-sm text-muted-foreground">
          No transfer route to {programName}. This card still earns — its
          rewards just can&apos;t be moved into this program.
        </p>
      ) : null}

      <div className="mt-5 grid gap-6 lg:grid-cols-3">
        <div>
          <Subheading>Earn rates</Subheading>
          <ul className="mt-2 space-y-2.5">
            {card.earn_rules.map((rule) => (
              <li key={rule.category_slug} className="text-sm">
                <div className="flex items-baseline justify-between gap-3">
                  <span className="flex flex-wrap items-center gap-x-2 gap-y-1 text-foreground">
                    {rule.category_label}
                    {rule.needs_verification ? <Unverified /> : null}
                  </span>
                  <span className="shrink-0 tabular-nums text-muted-foreground">
                    {trimRate(rule.earn_rate)}{" "}
                    {Number(rule.earn_rate) === 1 ? "pt" : "pts"}/₹100
                  </span>
                </div>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {programName
                    ? rule.miles_per_100
                      ? `${trimRate(rule.miles_per_100)} ${programName} miles per ₹100`
                      : "No route to this programme"
                    : `Earns ${card.currency_name}`}
                  {capNote(rule)}
                </p>
                {caps
                  .filter((cap) => cap.category_slug === rule.category_slug)
                  .map((cap) => (
                    <CapProgress key={cap.period} cap={cap} />
                  ))}
              </li>
            ))}
          </ul>
        </div>

        <div>
          <Subheading>Milestones</Subheading>
          {card.milestones.length === 0 ? (
            <p className="mt-2 text-sm text-muted-foreground">
              No spend milestones on this card.
            </p>
          ) : (
            <ul className="mt-2 space-y-2.5">
              {card.milestones.map((milestone) => (
                <li key={milestone.milestone_id} className="text-sm">
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="flex flex-wrap items-center gap-x-2 gap-y-1 text-foreground">
                      {milestone.spend_threshold_inr
                        ? `₹${inr.format(milestone.spend_threshold_inr)} ${periodLabel(milestone.period)}`
                        : "Welcome bonus"}
                      {milestone.needs_verification ? <Unverified /> : null}
                    </span>
                    <span className="shrink-0 tabular-nums text-gold">
                      +{inr.format(milestone.bonus_points)}
                    </span>
                  </div>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {programName
                      ? milestone.bonus_miles !== null
                        ? `Worth ${inr.format(milestone.bonus_miles)} ${programName} miles`
                        : "No route to this programme"
                      : `${inr.format(milestone.bonus_points)} ${card.currency_name}`}
                  </p>
                  {milestoneProgress.has(milestone.milestone_id) ? (
                    <MilestoneProgressLine
                      progress={
                        milestoneProgress.get(
                          milestone.milestone_id,
                        ) as MilestoneProgress
                      }
                      period={milestone.period}
                    />
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </div>

        <div>
          <Subheading>Transfers out</Subheading>
          {card.transfer_links.length === 0 ? (
            <p className="mt-2 text-sm text-muted-foreground">
              This card&apos;s rewards don&apos;t transfer anywhere —
              they&apos;re redeemed with the issuer.
            </p>
          ) : (
            <ul className="mt-2 space-y-2.5">
              {card.transfer_links.map((link) => (
                <li key={link.partner_id} className="text-sm">
                  <div className="flex items-baseline justify-between gap-3">
                    <span
                      className={`flex flex-wrap items-center gap-x-2 gap-y-1 ${
                        link.is_target ? "text-gold" : "text-foreground"
                      }`}
                    >
                      {link.program_name}
                      {link.needs_verification ? <Unverified /> : null}
                    </span>
                    <span className="shrink-0 tabular-nums text-muted-foreground">
                      {link.ratio_from}:{link.ratio_to}
                    </span>
                  </div>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {link.annual_ceiling_miles !== null
                      ? `Up to ${inr.format(link.annual_ceiling_miles)} miles a year`
                      : "No yearly cap"}
                    {link.transfer_fee_inr > 0
                      ? ` · ₹${inr.format(link.transfer_fee_inr)} per transfer`
                      : " · no fee"}
                    {` · ${processingLabel(link.processing_days_min, link.processing_days_max)}`}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </article>
  );
}

/**
 * "Which of my cards gets me into a lounge, on what condition, and what must
 * I activate?" — the in-the-moment question, answered per card.
 *
 * Coverage is partial and the section says so out loud. A card we have not
 * researched is rendered as "conditions not covered yet", NEVER folded in
 * with cards that genuinely have no lounge access — the cardholder is paying
 * for that benefit, and telling them it does not exist is the same class of
 * failure as a stale condition sending them to a desk to be turned away.
 */
function LoungeAccessSection({ portfolio }: { portfolio: WalletPortfolio }) {
  const withAccess = portfolio.cards.filter(
    (card) => card.lounge_coverage !== "none",
  );
  if (withAccess.length === 0) return null;

  return (
    <section>
      <SectionHeading icon={Armchair}>Lounge access</SectionHeading>
      <p className="mt-1.5 text-sm text-muted-foreground">
        What each card actually gets you at the airport — and what you have to
        do first.
      </p>
      <div className="mt-4 space-y-4">
        {withAccess.map((card) => (
          <article
            key={card.card_id}
            className="rounded-2xl border border-hairline bg-input/[0.05] p-5"
          >
            <header className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
              <h4 className="font-heading text-base text-foreground">
                {card.bank} {card.card_name}
              </h4>
              {card.lounge_coverage === "not_detailed" ? (
                <span className="text-xs text-muted-foreground">
                  conditions not covered yet
                </span>
              ) : null}
            </header>

            {card.lounge_coverage === "not_detailed" ? (
              <p className="mt-2 text-sm text-muted-foreground">
                This card has lounge access, but we haven&apos;t verified its
                conditions yet — check your card&apos;s terms for visit counts
                and any spend requirement. We&apos;d rather say nothing than
                guess the number.
              </p>
            ) : (
              <ul className="mt-3 space-y-3">
                {card.lounge_access.map((access) => (
                  <li
                    key={`${access.scope}-${access.program_name}-${access.spend_gate_inr}`}
                  >
                    <LoungeRow access={access} />
                  </li>
                ))}
              </ul>
            )}
          </article>
        ))}
      </div>
      {portfolio.lounge_cards_undetailed > 0 ? (
        <p className="mt-3 text-xs text-muted-foreground/80">
          {portfolio.lounge_cards_undetailed} of your {portfolio.cards.length}{" "}
          cards {portfolio.lounge_cards_undetailed === 1 ? "has" : "have"}{" "}
          lounge access we haven&apos;t detailed yet. Lounge terms in India
          change often, so we only publish conditions we&apos;ve checked against
          the issuer.
        </p>
      ) : null}
    </section>
  );
}

function LoungeRow({ access }: { access: PortfolioLoungeAccess }) {
  const where = access.scope === "domestic" ? "In India" : "Outside India";
  const allowance = access.is_unlimited
    ? "Unlimited visits"
    : access.visits_per_period === 0
      ? "No complimentary visits"
      : `${access.visits_per_period} visit${access.visits_per_period === 1 ? "" : "s"} per ${periodWord(access.period)}`;

  return (
    <div>
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <span className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[15px] text-foreground">
          <span>
            <span className="text-muted-foreground">{where}:</span> {allowance}
          </span>
          {access.needs_verification === true ? <Unverified /> : null}
        </span>
        <span className="shrink-0 text-xs text-muted-foreground">
          via {access.program_name}
        </span>
      </div>

      {/* The condition most cardholders get wrong, so it gets the loudest
          treatment on the page: these visits are EARNED by last period's
          spend, not granted with the card. */}
      {access.spend_gate_inr ? (
        <p className="mt-1.5 rounded-lg border border-gold/30 bg-gold/[0.06] px-3 py-2 text-xs text-gold">
          Only if you spent ₹{inr.format(access.spend_gate_inr)} or more in the
          previous {periodWord(access.spend_gate_period ?? access.period)} —
          these visits are earned, not automatic.
        </p>
      ) : null}

      <p className="mt-1 text-xs text-muted-foreground">
        {access.needs_activation
          ? "You must activate this first — it doesn't exist until you do."
          : "No activation needed."}
        {access.guest_visits_per_period === 0
          ? " Guests aren't covered."
          : access.guest_visits_per_period
            ? ` ${access.guest_visits_per_period} guest visit${access.guest_visits_per_period === 1 ? "" : "s"} included.`
            : ""}
        {!access.is_unlimited && access.reset_anchor !== "not_applicable"
          ? ` Resets on the ${anchorWord(access.reset_anchor)}.`
          : ""}
      </p>

      {access.conditions ? (
        <p className="mt-1 text-xs text-muted-foreground/80">
          {access.conditions}
        </p>
      ) : null}
    </div>
  );
}

function periodWord(period: string): string {
  return (
    {
      monthly: "month",
      quarterly: "quarter",
      half_yearly: "half-year",
      annual: "year",
      statement_cycle: "statement cycle",
      lifetime: "lifetime",
    }[period] ?? period
  );
}

function anchorWord(anchor: string): string {
  return (
    {
      calendar_quarter: "calendar quarter",
      calendar_year: "calendar year",
      card_anniversary: "card anniversary",
      statement_cycle: "statement cycle",
    }[anchor] ?? anchor
  );
}

function PartnerReach({ portfolio }: { portfolio: WalletPortfolio }) {
  if (portfolio.partner_reach.length === 0) return null;
  const byId = new Map(
    portfolio.cards.map((card) => [card.card_id, card.card_name]),
  );
  return (
    <section>
      <SectionHeading icon={Plane}>Where your points can go</SectionHeading>
      <ul className="mt-4 divide-y divide-hairline rounded-2xl border border-hairline">
        {portfolio.partner_reach.map((reach) => (
          <li
            key={reach.partner_id}
            className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 px-4 py-3"
          >
            <div>
              <p
                className={`text-[15px] font-medium ${reach.is_target ? "text-gold" : ""}`}
              >
                <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
                  {reach.program_name}
                  {reach.needs_verification === true ? <Unverified /> : null}
                </span>
              </p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                via {reach.card_ids.map((id) => byId.get(id) ?? "").join(", ")}
              </p>
            </div>
            <p className="text-sm tabular-nums text-muted-foreground">
              best {inr.format(reach.best_miles_per_1000_points)} miles per
              1,000 pts
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}

function SectionHeading({
  icon: Icon,
  children,
}: {
  icon: typeof Landmark;
  children: React.ReactNode;
}) {
  return (
    <h3 className="flex items-center gap-2 font-heading text-base text-foreground sm:text-lg">
      <Icon className="size-4 text-gold" aria-hidden="true" />
      {children}
    </h3>
  );
}

function Subheading({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-xs sm:text-[11px] uppercase tracking-[0.12em] text-muted-foreground">
      {children}
    </p>
  );
}

/**
 * A rule can be capped monthly, quarterly or annually — rendering only the
 * monthly one would silently drop a real cap the moment the catalog gains a
 * card capped by quarter, which is common on Indian travel cards.
 */
function capNote(rule: PortfolioEarnRule): string {
  const caps = [
    [rule.monthly_cap_inr, "month"] as const,
    [rule.quarterly_cap_inr, "quarter"] as const,
    [rule.annual_cap_inr, "year"] as const,
  ]
    .filter(([amount]) => amount)
    .map(([amount, period]) => `₹${inr.format(amount as number)}/${period}`);
  if (caps.length === 0) return "";
  // What spend past the cap earns is stated per rule by the catalog — never
  // assumed to be the base rate (SBI Cashback pays nothing past its cap).
  const after =
    rule.over_cap_earn === "nothing"
      ? ", then nothing"
      : rule.over_cap_earn === "base_rate"
        ? ", then the base rate"
        : "";
  return ` · bonus rate up to ${caps.join(" and ")}${after}`;
}

const CATEGORY_LABELS = new Map(
  SPEND_CATEGORIES.map((category) => [category.slug, category.label] as const),
);

function categoryLabel(category: PortfolioCategory): string {
  return CATEGORY_LABELS.get(category.category_slug) ?? category.category_label;
}

/** "16.6500" → "16.65", "4.0000" → "4". Display only; the engine keeps 4dp. */
function trimRate(value: string): string {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? String(Number(numeric.toFixed(4))) : value;
}

function periodLabel(period: string): string {
  return period === "annual"
    ? "a year"
    : period === "quarterly"
      ? "a quarter"
      : period === "monthly"
        ? "a month"
        : "";
}

function processingLabel(min: number, max: number): string {
  if (max === 0) return "instant";
  if (min === max) return `${max} days`;
  return `${min}–${max} days`;
}

/** The Listed-tier label: shown wherever a row's seed data is unverified. */
function Unverified() {
  return (
    <span className="inline-flex shrink-0 items-center rounded-full border border-hairline px-2 py-px text-xs font-normal uppercase tracking-[0.08em] text-muted-foreground">
      Unverified
    </span>
  );
}

/** Whole percent, rounded DOWN from the integers — "at least" must never
 *  round up past what the log shows. */
function floorPercent(part: number, whole: number): number {
  return whole > 0 ? Math.floor((part * 100) / whole) : 0;
}

function ProgressBar({ percent, label }: { percent: number; label: string }) {
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.min(100, percent)}
      className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-foreground/10"
    >
      <div
        className="h-full rounded-full bg-primary"
        style={{ width: `${Math.min(100, percent)}%` }}
      />
    </div>
  );
}

/**
 * How much of one accelerated-rate cap the log has used. A floor: spend the
 * user did not log is not counted, so "used" is at least and "left" is at most.
 */
function CapProgress({ cap }: { cap: CapUse }) {
  const percent = floorPercent(cap.logged_spend_inr, cap.cap_inr);
  return (
    <div className="mt-2 rounded-lg border border-hairline/70 bg-background/40 px-3 py-2">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5 text-xs">
        <span className="text-muted-foreground">
          Logged in {cap.window.label}
        </span>
        <span className="tabular-nums text-foreground">
          ₹{inr.format(cap.logged_spend_inr)} of ₹{inr.format(cap.cap_inr)}
        </span>
      </div>
      <ProgressBar
        percent={percent}
        label={`At least ${percent}% of this cap used`}
      />
      <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">
        {capCopy(cap, percent)}
      </p>
    </div>
  );
}

/**
 * Logged spend toward one milestone. Never "missed" or "not reached": an
 * unlogged rupee is not a missing rupee, so the log can only show a threshold
 * passed, or how much more would have to be logged to show it.
 */
function MilestoneProgressLine({
  progress,
  period,
}: {
  progress: MilestoneProgress;
  period: string;
}) {
  const where = progress.window
    ? `in ${progress.window.label}`
    : "across your whole log";
  const percent = floorPercent(
    progress.logged_spend_inr,
    progress.threshold_inr,
  );
  return (
    <div className="mt-2 rounded-lg border border-hairline/70 bg-background/40 px-3 py-2">
      {progress.status === "reached" ? (
        <p className="flex items-start gap-1.5 text-xs leading-relaxed text-foreground">
          <CheckCircle2
            className="mt-px size-3.5 shrink-0"
            aria-hidden="true"
          />
          <span>
            Your log shows ₹{inr.format(progress.logged_spend_inr)} {where} —
            past the ₹{inr.format(progress.threshold_inr)} threshold.
          </span>
        </p>
      ) : (
        <>
          <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5 text-xs">
            <span className="text-muted-foreground">Logged {where}</span>
            <span className="tabular-nums text-foreground">
              ₹{inr.format(progress.logged_spend_inr)} of ₹
              {inr.format(progress.threshold_inr)}
            </span>
          </div>
          <ProgressBar
            percent={percent}
            label={`At least ${percent}% of this milestone logged`}
          />
          <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">
            ₹{inr.format(progress.remaining_inr_at_most)} more to log before we
            can confirm it — you may already be closer.
          </p>
        </>
      )}
      {progress.anchor_assumed && progress.window ? (
        <p className="mt-1 text-xs leading-relaxed text-muted-foreground/80">
          Counted on the calendar {periodWord(period)}, which may differ from
          your statement cycle or card year.
        </p>
      ) : null}
    </div>
  );
}

function formatDate(iso: string): string {
  // Parsed as a calendar date, not an instant: "2026-09-01" must not slip to
  // 31 Aug in a timezone west of UTC.
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/**
 * The line under a cap's progress bar. "Used up" is only stated firmly when we
 * know the issuer's reset; on an assumed calendar window the user may still
 * have bonus room on their real statement cycle, so it is hedged.
 */
function capCopy(cap: CapUse, percent: number): string {
  const window = `the calendar ${periodWord(cap.period)}`;
  if (cap.remaining_inr_at_most === 0) {
    return cap.anchor_assumed
      ? `Your logged spend reaches this cap on ${window} — but if your issuer resets it on your statement cycle, you may still have bonus-rate room. Check your statement before assuming it is used.`
      : "Your logged spend has used this cap — more spend here stops earning the bonus rate until it resets (on some cards it earns nothing at all; see the card's earn rules).";
  }
  const used = percent > 0 ? `At least ${percent}% used · ` : "";
  const room = `${used}at most ₹${inr.format(cap.remaining_inr_at_most)} of bonus-rate room left.`;
  return cap.anchor_assumed
    ? `${room} Counted on ${window}, which may differ from your statement cycle.`
    : room;
}
