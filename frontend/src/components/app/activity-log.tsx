"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Armchair,
  CheckCircle2,
  CreditCard,
  Info,
  Loader2,
  Receipt,
  Plus,
  Trash2,
  Trophy,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { getAccessToken } from "@/lib/supabase";
import { useWallet } from "@/lib/wallet";
import {
  ApiError,
  SPEND_CATEGORIES,
  clearRenewalMonth,
  deleteLoungeVisit,
  deleteSpendEntry,
  fetchActivitySummary,
  fetchLoungeVisits,
  fetchSpendEntries,
  logLoungeVisit,
  logSpend,
  setRenewalMonth,
  type ActivitySummary,
  type CardSummary,
  type FeeWaiver,
  type FeeWaiverProgress,
  type LoungeAllowanceUse,
  type LoungeVisitEntry,
  type SpendEntry,
} from "@/lib/api";

const inr = new Intl.NumberFormat("en-IN");

/**
 * The activity log — one surface for both kinds of logging.
 *
 * ONE PATTERN, NOT TWO, by roadmap decision: "same entry surface, same mental
 * model — or users end up with two separate things to remember and do
 * neither." So spend and lounge visits share this page, share the form (card
 * and date sit in the same place in both modes; only the payload row differs),
 * and share the summary below.
 *
 * EVERY NUMBER HERE IS A BOUND, and the copy says so in words rather than
 * leaving it to a footnote. A log is a floor: the user forgets entries, they
 * do not invent them. So a milestone can be *reached* but never *missed*, and
 * lounge headroom reads "at most". Writing "1 visit left" as a fact is what
 * sends someone to a lounge desk to be turned away — the exact failure the
 * roadmap says is worse than showing no count at all.
 */

type Mode = "spend" | "lounge";

type Loaded = {
  summary: ActivitySummary;
  spend: SpendEntry[];
  visits: LoungeVisitEntry[];
};

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export function ActivityLog({ catalog }: { catalog: CardSummary[] }) {
  const { cardIds, hydrated } = useWallet();
  const [data, setData] = useState<Loaded | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Bumped after a write so the effect refetches. Cheaper and less error-prone
  // than threading the new row into local state — the summary is a derived
  // view of the whole log, so a partial update could disagree with it.
  const [reloadKey, setReloadKey] = useState(0);
  // Completed summary loads, success OR failure — lets a row release its
  // optimistic renewal-month pick even when the refetch fails.
  const [loads, setLoads] = useState(0);

  const cardName = useMemo(() => {
    const names = new Map(catalog.map((c) => [c.id, `${c.bank} ${c.card_name}`]));
    return (id: string) => names.get(id) ?? "Unknown card";
  }, [catalog]);

  // Only cards the catalog still lists — a stale wallet id would 404 the whole
  // summary, and the picker can't un-pick a card it can't render. Same guard
  // as portfolio-view.
  const known = useMemo(
    () => cardIds.filter((id) => catalog.some((card) => card.id === id)),
    [cardIds, catalog],
  );

  const reload = useCallback(() => setReloadKey((k) => k + 1), []);

  // No synchronous setState in the effect body (React lints it, and it
  // cascades renders): `loading` is derived below instead of being set here.
  useEffect(() => {
    if (!hydrated || known.length === 0) return;
    let cancelled = false;
    void (async () => {
      try {
        const token = await getAccessToken();
        if (!token) throw new ApiError("Please log in to see your log.", 401);
        const [summary, spend, visits] = await Promise.all([
          fetchActivitySummary(known, token),
          fetchSpendEntries(token),
          fetchLoungeVisits(token),
        ]);
        if (cancelled) return;
        setData({ summary, spend, visits });
        setError(null);
        setLoads((n) => n + 1);
      } catch (err) {
        if (cancelled) return;
        setError(
          err instanceof ApiError ? err.message : "Couldn't load your log.",
        );
        setLoads((n) => n + 1);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [hydrated, known, reloadKey]);

  const loading = hydrated && known.length > 0 && data === null && error === null;

  if (hydrated && known.length === 0) {
    return (
      <section className="rounded-2xl border border-hairline bg-input/[0.07] p-5 sm:p-6">
        <p className="text-sm font-semibold text-foreground">
          Add your cards first
        </p>
        <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
          The log counts what you spend and where you get in against the cards
          you actually hold. Pick them on the{" "}
          <a className="underline underline-offset-4" href="/cards">
            My cards
          </a>{" "}
          page and come back.
        </p>
      </section>
    );
  }

  return (
    <div className="space-y-10">
      <LogForm catalog={catalog} walletIds={known} onLogged={reload} />

      {error && (
        <p className="rounded-xl border border-destructive/40 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          {error}
        </p>
      )}

      {loading && (
        <p className="flex items-center gap-2 text-sm text-muted-foreground" role="status">
          <Loader2 className="size-4 animate-spin" /> Working out what your log
          proves…
        </p>
      )}

      {data && (
        <>
          <Caveat summary={data.summary} />
          <LoungeSection summary={data.summary} cardName={cardName} />
          <CapsSection summary={data.summary} cardName={cardName} />
          <MilestonesSection summary={data.summary} cardName={cardName} />
          <FeeWaiversSection
            summary={data.summary}
            cardName={cardName}
            loads={loads}
            onChanged={reload}
          />
          <RecentEntries data={data} cardName={cardName} onChanged={reload} />
        </>
      )}
    </div>
  );
}

/* ── The shared entry form ───────────────────────────────────────────────── */

function LogForm({
  catalog,
  walletIds,
  onLogged,
}: {
  catalog: CardSummary[];
  walletIds: string[];
  onLogged: () => void;
}) {
  const [mode, setMode] = useState<Mode>("spend");
  const [picked, setPicked] = useState<string>("");
  const [occurredOn, setOccurredOn] = useState(today());
  const [amount, setAmount] = useState("");
  const [category, setCategory] = useState<string>("default");
  const [scope, setScope] = useState<"domestic" | "international">("domestic");
  const [guests, setGuests] = useState("0");
  const [airport, setAirport] = useState("");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Derived during render rather than synced in an effect: if the wallet
  // changes under a stale selection, the first card is simply the answer.
  const cardId = walletIds.includes(picked) ? picked : (walletIds[0] ?? "");
  const wallet = catalog.filter((c) => walletIds.includes(c.id));

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setFormError(null);
    try {
      const token = await getAccessToken();
      if (!token) throw new ApiError("Please log in first.", 401);
      if (mode === "spend") {
        await logSpend(
          {
            card_id: cardId,
            occurred_on: occurredOn,
            amount_inr: Number(amount),
            category_slug: category,
          },
          token,
        );
        setAmount("");
      } else {
        await logLoungeVisit(
          {
            card_id: cardId,
            occurred_on: occurredOn,
            scope,
            guest_count: Number(guests) || 0,
            // Uppercased here so a lowercase "del" is accepted rather than
            // bounced by the server's IATA pattern.
            airport_code: airport ? airport.toUpperCase() : null,
          },
          token,
        );
        setAirport("");
        setGuests("0");
      }
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
      onLogged();
    } catch (err) {
      setFormError(
        err instanceof ApiError ? err.message : "Couldn't save that. Try again.",
      );
    } finally {
      setBusy(false);
    }
  }

  const fieldClass =
    "h-12 w-full rounded-xl border border-hairline bg-input/[0.07] px-3 text-sm text-foreground outline-none transition-colors focus:border-white/30 sm:h-10";
  const labelClass = "mb-1.5 block text-xs font-medium text-muted-foreground";

  return (
    <section className="rounded-2xl border border-hairline bg-input/[0.07] p-5 sm:p-6">
      {/* One control, two payloads — the card and date fields never move
          between modes, so logging either thing is the same gesture. */}
      <div
        className="inline-flex rounded-xl border border-hairline p-1"
        role="tablist"
        aria-label="What are you logging?"
      >
        {(
          [
            ["spend", "A spend", CreditCard],
            ["lounge", "A lounge visit", Armchair],
          ] as const
        ).map(([value, label, Icon]) => (
          <button
            key={value}
            type="button"
            role="tab"
            aria-selected={mode === value}
            onClick={() => setMode(value)}
            className={`flex min-h-11 items-center gap-2 rounded-lg px-3.5 text-sm font-medium transition-colors sm:min-h-9 ${
              mode === value
                ? "bg-foreground/10 text-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Icon className="size-4" />
            {label}
          </button>
        ))}
      </div>

      <form onSubmit={submit} className="mt-5 space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className={labelClass} htmlFor="log-card">
              Card
            </label>
            <select
              id="log-card"
              className={fieldClass}
              value={cardId}
              onChange={(e) => setPicked(e.target.value)}
              required
            >
              {wallet.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.bank} {c.card_name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelClass} htmlFor="log-date">
              Date
            </label>
            <input
              id="log-date"
              type="date"
              className={fieldClass}
              value={occurredOn}
              // A log records what happened, not what is planned — the server
              // rejects a future date, so don't offer one.
              max={today()}
              onChange={(e) => setOccurredOn(e.target.value)}
              required
            />
          </div>
        </div>

        {mode === "spend" ? (
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className={labelClass} htmlFor="log-amount">
                Amount (₹)
              </label>
              <input
                id="log-amount"
                type="number"
                min={1}
                inputMode="numeric"
                className={fieldClass}
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="45000"
                required
              />
            </div>
            <div>
              <label className={labelClass} htmlFor="log-category">
                Category
              </label>
              <select
                id="log-category"
                className={fieldClass}
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              >
                {SPEND_CATEGORIES.map((c) => (
                  <option key={c.slug} value={c.slug}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-3">
            <div>
              <label className={labelClass} htmlFor="log-scope">
                Domestic or international
              </label>
              <select
                id="log-scope"
                className={fieldClass}
                value={scope}
                onChange={(e) =>
                  setScope(e.target.value as "domestic" | "international")
                }
              >
                <option value="domestic">Domestic</option>
                <option value="international">International</option>
              </select>
            </div>
            <div>
              <label className={labelClass} htmlFor="log-airport">
                Airport (optional)
              </label>
              <input
                id="log-airport"
                className={`${fieldClass} uppercase`}
                value={airport}
                onChange={(e) => setAirport(e.target.value)}
                placeholder="DEL"
                maxLength={3}
              />
            </div>
            <div>
              <label className={labelClass} htmlFor="log-guests">
                Guests you brought
              </label>
              <input
                id="log-guests"
                type="number"
                min={0}
                inputMode="numeric"
                className={fieldClass}
                value={guests}
                onChange={(e) => setGuests(e.target.value)}
              />
            </div>
          </div>
        )}

        {formError && (
          <p className="text-sm text-destructive">{formError}</p>
        )}

        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" disabled={busy || !cardId}>
            {busy ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Plus className="size-4" />
            )}
            {mode === "spend" ? "Log this spend" : "Log this visit"}
          </Button>
          {saved && (
            <span
              className="flex items-center gap-1.5 text-sm text-muted-foreground"
              role="status"
            >
              <CheckCircle2 className="size-4" /> Saved
            </span>
          )}
        </div>
      </form>
    </section>
  );
}

/* ── The honesty line ────────────────────────────────────────────────────── */

function Caveat({ summary }: { summary: ActivitySummary }) {
  return (
    <div className="flex gap-3 rounded-xl border border-hairline bg-input/[0.07] px-4 py-3">
      <Info className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
      <div className="text-xs leading-relaxed text-muted-foreground">
        {/* Rendered from the API's own string rather than written here, so the
            caveat travels with the numbers it qualifies. */}
        <p>{summary.caveat}</p>
        {summary.earliest_entry_on && (
          <p className="mt-1">
            Your log starts on{" "}
            <span className="text-foreground">
              {formatDate(summary.earliest_entry_on)}
            </span>
            . Nothing before that is counted.
          </p>
        )}
      </div>
    </div>
  );
}

/* ── Lounge allowances ───────────────────────────────────────────────────── */

function LoungeSection({
  summary,
  cardName,
}: {
  summary: ActivitySummary;
  cardName: (id: string) => string;
}) {
  if (summary.lounge.length === 0 && summary.uncountable.length === 0) {
    return null;
  }
  return (
    <section>
      <SectionHeading
        icon={Armchair}
        title="Lounge access"
        blurb="What you have used, and what is left at most."
      />
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {summary.lounge.map((row) => (
          <LoungeRow
            key={`${row.card_id}-${row.scope}-${row.program_id}-${row.gate?.threshold_inr ?? 0}`}
            row={row}
            cardName={cardName}
          />
        ))}
      </div>
      {summary.uncountable.map((row) => (
        <p
          key={`${row.card_id}-${row.scope}`}
          className="mt-3 rounded-xl border border-hairline px-4 py-3 text-xs leading-relaxed text-muted-foreground"
        >
          <span className="text-foreground">{cardName(row.card_id)}</span> ·{" "}
          {row.scope}: {row.reason}
        </p>
      ))}
    </section>
  );
}

function LoungeRow({
  row,
  cardName,
}: {
  row: LoungeAllowanceUse;
  cardName: (id: string) => string;
}) {
  return (
    <div className="rounded-2xl border border-hairline p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-foreground">
            {cardName(row.card_id)}
          </p>
          <p className="text-xs text-muted-foreground">
            {/* `capitalize` on the scope alone — on the wrapper it also
                retitles the catalog's own programme names. */}
            <span className="capitalize">{row.scope}</span> ·{" "}
            {row.program_name}
          </p>
        </div>
        <p className="shrink-0 text-right font-heading text-lg text-foreground">
          {row.is_unlimited ? (
            "Unlimited"
          ) : (
            <>
              {row.visits_logged_at_least}
              <span className="text-muted-foreground">/{row.allowance}</span>
            </>
          )}
        </p>
      </div>

      {/* "at least" / "at most" in the copy, not just the field name — a
          reader who skips the caveat still gets the bound. */}
      {row.is_unlimited ? (
        <p className="mt-2 text-xs text-muted-foreground">
          No limit to track. You have logged {row.visits_logged_at_least}{" "}
          {row.visits_logged_at_least === 1 ? "visit" : "visits"}.
        </p>
      ) : row.allowance === 0 ? (
        <p className="mt-2 text-xs text-muted-foreground">
          This card grants no complimentary visits here — a membership is not
          the same as free entry.
        </p>
      ) : (
        <p className="mt-2 text-xs text-muted-foreground">
          At least {row.visits_logged_at_least} used
          {row.window ? ` in ${row.window.label}` : ""} · at most{" "}
          <span className="text-foreground">{row.remaining_at_most}</span> left.
        </p>
      )}

      {row.guest_visits_logged > 0 && (
        <p className="mt-1 text-xs text-muted-foreground">
          {row.guest_visits_logged} guest{" "}
          {row.guest_visits_logged === 1 ? "visit" : "visits"} logged
          {row.guests_share_allowance
            ? " — these come out of your own allowance."
            : " — these do not come out of your own allowance."}
        </p>
      )}

      {row.gate && (
        <p
          className={`mt-3 rounded-lg px-3 py-2 text-xs leading-relaxed ${
            row.gate.status === "reached"
              ? "bg-foreground/[0.06] text-muted-foreground"
              : "bg-primary/10 text-foreground"
          }`}
        >
          {row.gate.status === "reached" ? (
            <>
              Unlocked: you logged ₹{inr.format(row.gate.logged_spend_inr)} in{" "}
              {row.gate.window.label}, clearing the ₹
              {inr.format(row.gate.threshold_inr)} needed.
            </>
          ) : (
            <>
              Needs ₹{inr.format(row.gate.threshold_inr)} spent in{" "}
              <span className="font-medium">{row.gate.window.label}</span> — the
              quarter <em>before</em> this one. You have logged ₹
              {inr.format(row.gate.logged_spend_inr)} of it, so we cannot
              confirm these visits are unlocked. Check with your issuer before
              relying on them.
            </>
          )}
        </p>
      )}

      {row.enrollment_required && (
        <p className="mt-2 text-xs text-muted-foreground">
          You must activate this first.{" "}
          {row.enrollment_url && (
            <a
              className="underline underline-offset-4"
              href={row.enrollment_url}
              target="_blank"
              rel="noreferrer"
            >
              Enrol here
            </a>
          )}
        </p>
      )}
    </div>
  );
}

/* ── Caps ────────────────────────────────────────────────────────────────── */

function CapsSection({
  summary,
  cardName,
}: {
  summary: ActivitySummary;
  cardName: (id: string) => string;
}) {
  if (summary.caps.length === 0) return null;
  return (
    <section>
      <SectionHeading
        icon={CreditCard}
        title="Accelerated-earning caps"
        blurb="How much of each bonus-rate cap your logged spend has already used."
      />
      <div className="mt-4 space-y-3">
        {summary.caps.map((cap) => {
          const pct = Math.min(100, Number(cap.fraction_used_at_least) * 100);
          return (
            <div
              key={`${cap.card_id}-${cap.category_slug}-${cap.period}`}
              className="rounded-2xl border border-hairline p-4"
            >
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <p className="text-sm font-medium text-foreground">
                  {cardName(cap.card_id)} · {cap.category_label}
                </p>
                <p className="text-xs text-muted-foreground">
                  ₹{inr.format(cap.logged_spend_inr)} of ₹
                  {inr.format(cap.cap_inr)} · {cap.window.label}
                </p>
              </div>
              <div className="mt-2.5 h-1.5 overflow-hidden rounded-full bg-foreground/10">
                <div
                  className="h-full rounded-full bg-primary"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <p className="mt-2 text-xs text-muted-foreground">
                At most ₹{inr.format(cap.remaining_inr_at_most)} of bonus-rate
                room left
                {cap.anchor_assumed && (
                  // The catalog states the cap's period but not what it resets
                  // against; most Indian caps run on the statement cycle. Say
                  // so rather than implying we know.
                  <>
                    {" "}
                    · counted on the calendar {cap.period.replace("ly", "")},
                    which may differ from your statement cycle
                  </>
                )}
                .
              </p>
            </div>
          );
        })}
      </div>
    </section>
  );
}

/* ── Milestones ──────────────────────────────────────────────────────────── */

function MilestonesSection({
  summary,
  cardName,
}: {
  summary: ActivitySummary;
  cardName: (id: string) => string;
}) {
  if (summary.milestones.length === 0) return null;
  return (
    <section>
      <SectionHeading
        icon={Trophy}
        title="Milestone progress"
        blurb="Bonus points you are walking toward, from what you have logged."
      />
      <div className="mt-4 space-y-3">
        {summary.milestones.map((m) => (
          <div
            key={m.milestone_id}
            className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-hairline p-4"
          >
            <div>
              <p className="text-sm font-medium text-foreground">
                {cardName(m.card_id)} · ₹{inr.format(m.threshold_inr)} →{" "}
                {inr.format(m.bonus_points)} points
              </p>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {m.window ? m.window.label : "One-off"} · logged ₹
                {inr.format(m.logged_spend_inr)}
              </p>
            </div>
            {m.status === "reached" ? (
              <span className="flex items-center gap-1.5 text-sm text-foreground">
                <CheckCircle2 className="size-4" /> Reached
              </span>
            ) : (
              // Never "not reached": an unlogged rupee is not a missing rupee.
              <span className="text-right text-xs text-muted-foreground">
                ₹{inr.format(m.remaining_inr_at_most)} more to log
                <br />
                before we can confirm it
              </span>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

/* ── Annual-fee waivers ──────────────────────────────────────────────────── */

const MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

/**
 * Fee-waiver progress, tracked ONLY where the user has told us the card's
 * renewal month. Without it we say so and ask — the waiver is measured over
 * the year before the renewal, and assuming a window would make the number a
 * guess (decision log 2026-11-02-fee-waiver-progress).
 *
 * Four answers, rendered four ways: tracked, needs a renewal month, a sourced
 * "no waiver", and "not checked yet". The last two must never look alike.
 */
function FeeWaiversSection({
  summary,
  cardName,
  loads,
  onChanged,
}: {
  summary: ActivitySummary;
  cardName: (id: string) => string;
  loads: number;
  onChanged: () => void;
}) {
  const rows = summary.fee_waivers ?? [];
  if (rows.length === 0) return null;
  const anyTracked = rows.some((row) => row.coverage === "tracked");
  return (
    <section>
      <SectionHeading
        icon={Receipt}
        title="Annual-fee waivers"
        blurb="Whether your logged spend has already earned a card its fee waiver."
      />
      {anyTracked && (
        // Once for the section, not on every card: the rule is the same
        // everywhere (periods.renewal_window).
        <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
          We count whole months only, so spend in a card&apos;s renewal month
          itself is left out — without the exact day it could fall either side
          of the renewal.
        </p>
      )}
      <div className="mt-4 space-y-3">
        {rows.map((row) => (
          <FeeWaiverRow
            key={row.card_id}
            row={row}
            name={cardName(row.card_id)}
            loads={loads}
            onChanged={onChanged}
          />
        ))}
      </div>
    </section>
  );
}

function waiverTerms(w: FeeWaiver): string {
  const amount = `₹${inr.format(w.threshold_inr ?? 0)}`;
  const spend =
    w.threshold_comparison === "more_than"
      ? `Spend more than ${amount}`
      : `Spend ${amount}`;
  const when =
    w.window_kind === "current_card_year"
      ? "during a card year and that year's fee is reversed"
      : w.window_kind === "days_365_before_fee_date"
        ? "in the 365 days before your fee date and the annual fee is waived"
        : "in the year before your renewal and the renewal fee is waived";
  const firstYear = w.waives_joining_fee ? " (the first-year fee too)" : "";
  return `${spend} ${when}${firstYear}.`;
}

function excludedNote(w: FeeWaiver): string | null {
  if (w.excluded_categories.length === 0) return null;
  const labels = w.excluded_categories.map(
    (slug) =>
      SPEND_CATEGORIES.find((c) => c.slug === slug)?.label.toLowerCase() ??
      slug,
  );
  return `We leave out ${labels.join(" and ")} spend — the issuer does not count it.`;
}

function FeeWaiverRow({
  row,
  name,
  loads,
  onChanged,
}: {
  row: FeeWaiverProgress;
  name: string;
  /** Completed summary loads (success or failure) — releases a pending pick. */
  loads: number;
  onChanged: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [rowError, setRowError] = useState<string | null>(null);
  // Optimistic pick: shown from the moment it is saved until the NEXT summary
  // load completes (`loads` moves on), so the select never snaps back to the
  // old month while the refetch is in flight. Derived during render rather
  // than cleared in an effect.
  const [pending, setPending] = useState<{ value: string; at: number } | null>(
    null,
  );
  const pendingActive = pending !== null && pending.at === loads;
  const waiver = row.waiver;
  const spendBased = waiver?.kind === "spend_based";
  const selectId = `renewal-${row.card_id}`;
  const hintId = `${selectId}-hint`;
  const errorId = `${selectId}-error`;

  async function choose(value: string) {
    // One save at a time: the select is disabled while busy or pending, and
    // this guard covers a change event that slips in before the re-render.
    if (busy || pendingActive) return;
    setBusy(true);
    setRowError(null);
    setPending({ value, at: loads });
    try {
      const token = await getAccessToken();
      if (!token) throw new ApiError("Please log in first.", 401);
      if (value === "") await clearRenewalMonth(row.card_id, token);
      else await setRenewalMonth(row.card_id, Number(value), token);
      onChanged();
    } catch (err) {
      setPending(null); // roll back to the saved month
      setRowError(
        err instanceof ApiError ? err.message : "Couldn't save that. Try again.",
      );
    } finally {
      setBusy(false);
    }
  }

  const saving = busy || pendingActive;
  const shownMonth = pendingActive
    ? pending.value
    : String(row.renewal_month ?? "");
  const count = row.count;
  const threshold = waiver?.threshold_inr ?? 0;
  const percent =
    count && threshold
      ? Math.min(
          100,
          // Floored: "at least" must never round up past what the log shows.
          Math.floor((count.logged_spend_inr * 100) / threshold),
        )
      : 0;
  // HSBC-style waivers reverse the fee charged at the START of the card year,
  // so "your Jun 2027 renewal" would name the wrong fee — name the fee.
  const target = count
    ? waiver?.window_kind === "current_card_year"
      ? `${count.decides_fee_label} fee (the card year ending at your ${count.renewal_label} renewal)`
      : `${count.renewal_label} renewal`
    : "";
  const describedBy =
    [row.coverage === "needs_renewal_month" ? hintId : null, rowError ? errorId : null]
      .filter(Boolean)
      .join(" ") || undefined;

  return (
    <div className="rounded-2xl border border-hairline p-4">
      <div className="flex flex-wrap items-center gap-2">
        <p className="min-w-0 text-sm font-medium text-foreground">{name}</p>
        {row.needs_verification ? <UnverifiedPill /> : null}
      </div>

      {row.coverage === "not_covered" && (
        <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
          {row.reason ?? "We have not checked this card's annual-fee waiver yet."}{" "}
          That is not the same as saying it has none.
        </p>
      )}

      {row.coverage === "no_waiver" && waiver && (
        <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
          {waiver.conditions ?? row.reason}
        </p>
      )}

      {spendBased && waiver && (
        <>
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
            {waiverTerms(waiver)}
            {excludedNote(waiver) ? <> {excludedNote(waiver)}</> : null}
          </p>
          {waiver.unmodelled_exclusions.length > 0 && (
            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
              The issuer also excludes:{" "}
              <span className="text-foreground">
                {waiver.unmodelled_exclusions.join(", ")}
              </span>
              . We can&apos;t separate these in your log, so leave them out
              when you log spend on this card.
            </p>
          )}
          {waiver.conditions && (
            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
              {waiver.conditions}
            </p>
          )}

          <div className="mt-3 max-w-xs">
            <label
              className="mb-1.5 block text-xs font-medium text-muted-foreground"
              htmlFor={selectId}
            >
              Renewal month (when the annual fee is charged)
            </label>
            <div className="flex items-center gap-2">
              <select
                id={selectId}
                className="h-12 w-full rounded-xl border border-hairline bg-input/[0.07] px-3 text-sm text-foreground outline-none transition-colors focus:border-white/30 disabled:opacity-60 sm:h-11"
                value={shownMonth}
                disabled={saving}
                aria-describedby={describedBy}
                onChange={(e) => void choose(e.target.value)}
              >
                <option value="">Not set</option>
                {MONTHS.map((month, index) => (
                  <option key={month} value={String(index + 1)}>
                    {month}
                  </option>
                ))}
              </select>
              {saving && (
                <span role="status" className="flex shrink-0 items-center">
                  <Loader2
                    className="size-4 animate-spin text-muted-foreground"
                    aria-hidden="true"
                  />
                  <span className="sr-only">Saving…</span>
                </span>
              )}
            </div>
          </div>
          {rowError && (
            <p id={errorId} className="mt-2 text-xs text-destructive" role="alert">
              {rowError}
            </p>
          )}

          {row.coverage === "needs_renewal_month" && (
            <p id={hintId} className="mt-2 text-xs leading-relaxed text-muted-foreground">
              Tell us your renewal month to track this. We won&apos;t guess
              the window.
            </p>
          )}

          {count && (
            <div className="mt-3">
              <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                <p className="text-xs text-muted-foreground">
                  Logged at least{" "}
                  <span className="text-foreground">
                    ₹{inr.format(count.logged_spend_inr)}
                  </span>{" "}
                  of ₹{inr.format(threshold)}
                </p>
                <p className="text-xs text-muted-foreground">
                  {count.window.label}
                </p>
              </div>
              <div
                className="mt-2 h-1.5 overflow-hidden rounded-full bg-foreground/10"
                role="img"
                aria-label={`At least ${percent}% of the waiver threshold logged`}
              >
                <div
                  className="h-full rounded-full bg-primary"
                  style={{ width: `${percent}%` }}
                />
              </div>
              {count.status === "reached" ? (
                <p className="mt-2 flex items-start gap-1.5 text-sm text-foreground">
                  <CheckCircle2 className="mt-0.5 size-4 shrink-0" />
                  <span>
                    {count.subject_to_exclusions
                      ? `Reached on your log for your ${target} — subject to the issuer's exclusions listed.`
                      : `Reached for your ${target} — your log alone proves it.`}
                  </span>
                </p>
              ) : (
                // Never "missed": an unlogged rupee is not a missing rupee.
                <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
                  At most{" "}
                  <span className="text-foreground">
                    ₹{inr.format(count.remaining_inr_at_most)}
                  </span>{" "}
                  {waiver.threshold_comparison === "more_than" && (
                    // In whole rupees the least qualifying spend is one
                    // rupee past the figure — say why the number is odd.
                    <>(spend must exceed ₹{inr.format(threshold)}) </>
                  )}
                  more to log before we can confirm the waiver for your{" "}
                  {target}.
                </p>
              )}
              {count.note && (
                <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                  {count.note}
                </p>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function UnverifiedPill() {
  return (
    <span
      className="inline-flex shrink-0 items-center rounded-full border border-hairline px-2 py-px text-xs font-normal uppercase tracking-[0.08em] text-muted-foreground"
      title="From a published source we haven't checked line by line yet"
    >
      Unverified
    </span>
  );
}

/* ── Recent entries ──────────────────────────────────────────────────────── */

function RecentEntries({
  data,
  cardName,
  onChanged,
}: {
  data: Loaded;
  cardName: (id: string) => string;
  onChanged: () => void;
}) {
  const [removing, setRemoving] = useState<string | null>(null);

  const rows = useMemo(() => {
    const spend = data.spend.map((e) => ({
      id: e.id,
      kind: "spend" as const,
      on: e.occurred_on,
      card: e.card_id,
      detail: `₹${inr.format(e.amount_inr)} · ${
        SPEND_CATEGORIES.find((c) => c.slug === e.category_slug)?.label ??
        e.category_slug
      }`,
    }));
    const visits = data.visits.map((v) => ({
      id: v.id,
      kind: "lounge" as const,
      on: v.occurred_on,
      card: v.card_id,
      detail: `${v.scope === "domestic" ? "Domestic" : "International"} lounge${
        v.airport_code ? ` · ${v.airport_code}` : ""
      }${v.guest_count ? ` · +${v.guest_count} guest` : ""}`,
    }));
    // Both kinds interleave in one list — the point of a single log.
    return [...spend, ...visits].sort((a, b) => b.on.localeCompare(a.on));
  }, [data]);

  if (rows.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Nothing logged yet. Everything above will fill in as you add entries.
      </p>
    );
  }

  async function remove(id: string, kind: "spend" | "lounge") {
    setRemoving(id);
    try {
      const token = await getAccessToken();
      if (!token) return;
      if (kind === "spend") await deleteSpendEntry(id, token);
      else await deleteLoungeVisit(id, token);
      onChanged();
    } finally {
      setRemoving(null);
    }
  }

  return (
    <section>
      <SectionHeading
        icon={CreditCard}
        title="Your log"
        blurb="Everything you have recorded, newest first."
      />
      <ul className="mt-4 divide-y divide-hairline rounded-2xl border border-hairline">
        {rows.map((row) => (
          <li
            key={row.id}
            className="flex flex-wrap items-center justify-between gap-3 px-4 py-3"
          >
            <div className="min-w-0">
              <p className="truncate text-sm text-foreground">{row.detail}</p>
              <p className="text-xs text-muted-foreground">
                {formatDate(row.on)} · {cardName(row.card)}
              </p>
            </div>
            <button
              type="button"
              onClick={() => remove(row.id, row.kind)}
              disabled={removing === row.id}
              aria-label="Delete this entry"
              className="flex min-h-11 shrink-0 items-center gap-1.5 px-2 text-xs text-muted-foreground transition-colors hover:text-destructive sm:min-h-0"
            >
              {removing === row.id ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Trash2 className="size-4" />
              )}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

/* ── Shared bits ─────────────────────────────────────────────────────────── */

function SectionHeading({
  icon: Icon,
  title,
  blurb,
}: {
  icon: typeof Armchair;
  title: string;
  blurb: string;
}) {
  return (
    <div>
      <h3 className="flex items-center gap-2 font-heading text-lg text-foreground">
        <Icon className="size-4 text-muted-foreground" />
        {title}
      </h3>
      <p className="mt-1 text-sm text-muted-foreground">{blurb}</p>
    </div>
  );
}

function formatDate(iso: string): string {
  // Parsed as parts, not `new Date(iso)`, which would read a bare date as UTC
  // midnight and shift it a day back for anyone west of Greenwich.
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}
