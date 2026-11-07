"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";
import { Check, ChevronDown, MapPin, Minus, Plus, Search } from "lucide-react";

import type { CabinClass, CityOption, RouteCoverage } from "@/lib/api";

/** Every cabin, in travel order. Uncovered ones render disabled, so the user
 * sees what exists and what we can't price yet — never a dead end later. */
export const ALL_CABINS: { value: CabinClass; label: string }[] = [
  { value: "economy", label: "Economy" },
  { value: "premium_economy", label: "Premium economy" },
  { value: "business", label: "Business" },
  { value: "first", label: "First" },
];

export const MAX_MONTHS_AHEAD = 36;
export const MAX_TRAVELLERS = 9;

/** Cabins with award data between two cities, per the coverage payload. */
export function cabinsFor(
  coverage: RouteCoverage,
  originCity: string,
  destinationCity: string,
): CabinClass[] {
  const region = (list: CityOption[], city: string) =>
    list.find((c) => c.city === city)?.region;
  const from = region(coverage.origins, originCity);
  const to = region(coverage.destinations, destinationCity);
  return (
    coverage.routes.find(
      (r) => r.origin_region === from && r.destination_region === to,
    )?.cabins ?? []
  );
}

/** "Dec 2027" for N months from today — the same arithmetic the engine uses
 * for the target date (today + N months). */
export function monthLabel(monthsAhead: number, today = new Date()): string {
  const target = new Date(today.getFullYear(), today.getMonth() + monthsAhead, 1);
  return target.toLocaleDateString("en-IN", { month: "short", year: "numeric" });
}

export function GoalForm({
  coverage,
  origin,
  destination,
  cabin,
  monthsAhead,
  passengers,
  onOrigin,
  onDestination,
  onCabin,
  onMonthsAhead,
  onPassengers,
}: {
  coverage: RouteCoverage;
  origin: string;
  destination: string;
  cabin: CabinClass;
  monthsAhead: number;
  passengers: number;
  onOrigin: (city: string) => void;
  onDestination: (city: string) => void;
  onCabin: (cabin: CabinClass) => void;
  onMonthsAhead: (months: number) => void;
  onPassengers: (count: number) => void;
}) {
  const available = cabinsFor(coverage, origin, destination);
  const unavailable = ALL_CABINS.filter((c) => !available.includes(c.value));

  return (
    <div className="mt-5 grid gap-5 sm:grid-cols-2">
      <Field label="Flying from">
        <CityCombobox
          label="Flying from"
          options={coverage.origins}
          value={origin}
          onChange={onOrigin}
        />
      </Field>
      <Field label="Flying to">
        <CityCombobox
          label="Flying to"
          options={coverage.destinations}
          value={destination}
          onChange={onDestination}
        />
      </Field>

      <Field label="Cabin" className="sm:col-span-2">
        <div
          role="radiogroup"
          aria-label="Cabin"
          className="grid grid-cols-2 gap-2 sm:grid-cols-4"
          // WAI-ARIA radio pattern: one Tab stop (the checked cabin); arrows
          // move between the covered cabins, skipping disabled ones.
          onKeyDown={(e) => {
            const step =
              e.key === "ArrowRight" || e.key === "ArrowDown"
                ? 1
                : e.key === "ArrowLeft" || e.key === "ArrowUp"
                  ? -1
                  : 0;
            if (step === 0 || available.length === 0) return;
            e.preventDefault();
            const at = available.indexOf(cabin);
            const next = available[(at + step + available.length) % available.length];
            onCabin(next);
            e.currentTarget
              .querySelector<HTMLButtonElement>(`[data-cabin="${next}"]`)
              ?.focus();
          }}
        >
          {ALL_CABINS.map((option) => {
            const enabled = available.includes(option.value);
            const selected = option.value === cabin;
            return (
              <button
                key={option.value}
                type="button"
                role="radio"
                data-cabin={option.value}
                aria-checked={selected}
                tabIndex={selected ? 0 : -1}
                disabled={!enabled}
                title={enabled ? undefined : `Not priceable to ${destination} yet`}
                onClick={() => onCabin(option.value)}
                className={`min-h-11 rounded-xl border px-3 py-2 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold/60 disabled:cursor-not-allowed disabled:opacity-50 ${
                  selected
                    ? "border-gold bg-gold/10 font-medium text-gold"
                    : "border-white/10 text-foreground hover:border-white/25"
                }`}
              >
                {option.label}
              </button>
            );
          })}
        </div>
        {unavailable.length > 0 && available.length > 0 ? (
          <p className="mt-2 text-xs text-muted-foreground">
            {listJoin(unavailable.map((c) => c.label))}{" "}
            {unavailable.length === 1 ? "isn't" : "aren't"} covered to{" "}
            {destination} yet — we only show what we can actually price.
          </p>
        ) : null}
      </Field>

      <Field label="When do you want to fly?">
        <div className="relative">
          <select
            aria-label="Travel month"
            value={monthsAhead}
            onChange={(e) => onMonthsAhead(Number(e.target.value))}
            className="h-11 w-full appearance-none rounded-xl border border-white/10 bg-transparent pl-3 pr-9 text-sm text-foreground focus:border-gold focus:outline-none"
          >
            {Array.from({ length: MAX_MONTHS_AHEAD }, (_, i) => i + 1).map((n) => (
              <option key={n} value={n} className="bg-popover">
                {monthLabel(n)}
              </option>
            ))}
          </select>
          <ChevronDown
            aria-hidden="true"
            className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
          />
        </div>
        <p className="mt-1.5 text-xs text-muted-foreground">
          {monthsAhead === 1 ? "Next month" : `In ${monthsAhead} months`} — the
          time you have to earn the miles.
        </p>
      </Field>

      <Field label="Travellers">
        <div className="flex h-11 items-center justify-between rounded-xl border border-white/10">
          <StepButton
            label="One fewer traveller"
            disabled={passengers <= 1}
            onClick={() => onPassengers(passengers - 1)}
          >
            <Minus className="size-4" />
          </StepButton>
          <span aria-live="polite" className="text-sm tabular-nums text-foreground">
            {passengers} {passengers === 1 ? "traveller" : "travellers"}
          </span>
          <StepButton
            label="One more traveller"
            disabled={passengers >= MAX_TRAVELLERS}
            onClick={() => onPassengers(passengers + 1)}
          >
            <Plus className="size-4" />
          </StepButton>
        </div>
      </Field>
    </div>
  );
}

function Field({
  label,
  className = "",
  children,
}: {
  label: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={`min-w-0 ${className}`}>
      <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </p>
      {children}
    </div>
  );
}

function StepButton({
  label,
  disabled,
  onClick,
  children,
}: {
  label: string;
  disabled: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      disabled={disabled}
      onClick={onClick}
      className="-m-px flex size-11 shrink-0 items-center justify-center rounded-xl text-foreground hover:bg-white/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold/60 disabled:opacity-30"
    >
      {children}
    </button>
  );
}

/** A searchable single-select limited to `options` (WAI-ARIA combobox with
 * a listbox popup). Typing filters; Enter/click picks; Escape or blur
 * restores the committed city — free text never escapes as a value. */
function CityCombobox({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: CityOption[];
  value: string;
  onChange: (city: string) => void;
}) {
  const listId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [highlight, setHighlight] = useState(0);

  const matches = useMemo(() => {
    const q = query.trim().toLowerCase();
    return q ? options.filter((o) => o.city.toLowerCase().includes(q)) : options;
  }, [options, query]);

  // Keep the highlighted option visible as the list opens (on the current
  // city) and as arrow keys move through a list taller than its box.
  useEffect(() => {
    if (!open) return;
    document
      .getElementById(`${listId}-${highlight}`)
      ?.scrollIntoView({ block: "nearest" });
  }, [open, highlight, listId]);

  const commit = (city: string) => {
    onChange(city);
    setQuery("");
    setOpen(false);
  };

  const openList = () => {
    setQuery("");
    setHighlight(Math.max(matches.findIndex((o) => o.city === value), 0));
    setOpen(true);
  };

  return (
    <div className="relative">
      <MapPin
        aria-hidden="true"
        className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
      />
      <input
        ref={inputRef}
        role="combobox"
        aria-label={label}
        aria-expanded={open}
        aria-controls={open ? listId : undefined}
        aria-autocomplete="list"
        aria-activedescendant={open && matches[highlight] ? `${listId}-${highlight}` : undefined}
        value={open ? query : value}
        placeholder={open ? value : undefined}
        onFocus={openList}
        onClick={() => (open ? null : openList())}
        onBlur={() => {
          setOpen(false);
          setQuery("");
        }}
        onChange={(e) => {
          setQuery(e.target.value);
          setHighlight(0);
          setOpen(true);
        }}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown") {
            e.preventDefault();
            if (!open) openList();
            else setHighlight((h) => Math.min(h + 1, matches.length - 1));
          } else if (e.key === "ArrowUp") {
            e.preventDefault();
            setHighlight((h) => Math.max(h - 1, 0));
          } else if (e.key === "Enter" && open) {
            e.preventDefault();
            if (matches[highlight]) commit(matches[highlight].city);
          } else if (e.key === "Escape") {
            setOpen(false);
            setQuery("");
          }
        }}
        className="h-11 w-full rounded-xl border border-white/10 bg-transparent pl-9 pr-9 text-sm text-foreground placeholder:text-muted-foreground/70 focus:border-gold focus:outline-none"
      />
      {open ? (
        <Search
          aria-hidden="true"
          className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
        />
      ) : (
        <ChevronDown
          aria-hidden="true"
          className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
        />
      )}
      {open ? (
        <ul
          id={listId}
          role="listbox"
          aria-label={label}
          // preventDefault: pressing the scrollbar must not blur the input.
          onMouseDown={(e) => e.preventDefault()}
          className="absolute z-30 mt-1.5 max-h-64 w-full overflow-y-auto rounded-xl border border-white/10 bg-popover p-1 shadow-xl"
        >
          {matches.length === 0 ? (
            <li className="px-3 py-2.5 text-sm text-muted-foreground">
              We don&apos;t cover &ldquo;{query.trim()}&rdquo; yet.
            </li>
          ) : (
            matches.map((option, index) => (
              <li
                key={option.city}
                id={`${listId}-${index}`}
                role="option"
                aria-selected={option.city === value}
                // mousedown, not click: it lands before the input's blur
                // closes the list.
                onMouseDown={(e) => {
                  e.preventDefault();
                  commit(option.city);
                }}
                onMouseMove={() => setHighlight(index)}
                className={`flex min-h-10 cursor-pointer items-center justify-between rounded-lg px-3 text-sm ${
                  index === highlight ? "bg-white/5 text-foreground" : "text-muted-foreground"
                }`}
              >
                <span>{option.city}</span>
                {option.city === value ? (
                  <Check aria-hidden="true" className="size-4 text-gold" />
                ) : null}
              </li>
            ))
          )}
        </ul>
      ) : null}
    </div>
  );
}

function listJoin(items: string[]): string {
  if (items.length <= 1) return items.join("");
  return `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
}
