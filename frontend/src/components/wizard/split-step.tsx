"use client";

import { ArrowRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

/**
 * The opt-in category split (decisions 6–7, slice 7). "Want a spending
 * strategy?" — No still yields a full strategy on the assumed template split
 * (with a visible caveat and one-click refine at the result); Yes opens the
 * categories-win editor: rows pre-filled from the template scaled to the
 * user's total, edits free, the shown total re-derives from the sum. No
 * "must equal" validation — once the user engages, their split is the truth.
 */

// The backend's default template proportions (pipeline/context.py
// DEFAULT_SPEND_PROFILE: 25/20/20/15/10 of 90). Pre-fills only — the user's
// edits win from the first keystroke.
export const SPLIT_CATEGORIES: { slug: string; label: string; weight: number }[] = [
  { slug: "travel", label: "Travel", weight: 25_000 },
  { slug: "dining", label: "Dining", weight: 20_000 },
  { slug: "online", label: "Online shopping", weight: 20_000 },
  { slug: "groceries", label: "Groceries", weight: 15_000 },
  { slug: "utilities", label: "Utilities", weight: 10_000 },
];
const WEIGHT_SUM = 90_000;

/** Template proportions scaled to the user's total-over-horizon (floored per
 * category, like the server's own derivation). */
export function prefillSplit(basisTotal: number): Record<string, string> {
  return Object.fromEntries(
    SPLIT_CATEGORIES.map((c) => [
      c.slug,
      String(Math.floor((basisTotal * c.weight) / WEIGHT_SUM)),
    ]),
  );
}

export function SplitStep({
  months,
  engaged,
  values,
  onEngage,
  onDecline,
  onChange,
  onBuild,
  building,
}: {
  months: number;
  /** null = not asked yet (show the ask); true = editor open. */
  engaged: boolean | null;
  values: Record<string, string>;
  onEngage: () => void;
  onDecline: () => void;
  onChange: (slug: string, value: string) => void;
  onBuild: () => void;
  building: boolean;
}) {
  if (engaged !== true) {
    return (
      <div className="mt-3">
        <p className="max-w-2xl text-sm text-muted-foreground">
          Tell us roughly where the money goes and we&apos;ll route every
          category to the card that earns it best — or skip it and we&apos;ll
          assume a typical split.
        </p>
        <div className="mt-5 flex flex-wrap gap-3">
          <Button
            onClick={onEngage}
            className="bg-gold text-gold-foreground hover:bg-gold/90"
          >
            Yes, split my spending
          </Button>
          <Button
            onClick={onDecline}
            disabled={building}
            variant="outline"
            className="border-hairline text-muted-foreground hover:border-gold/40 hover:text-gold"
          >
            Skip — use a typical split
            <ArrowRight />
          </Button>
        </div>
      </div>
    );
  }

  const total = SPLIT_CATEGORIES.reduce(
    (sum, c) => sum + Math.max(Math.round(Number(values[c.slug]) || 0), 0),
    0,
  );
  const monthly = Math.floor(total / months);

  return (
    <div className="mt-3">
      <p className="max-w-2xl text-sm text-muted-foreground">
        Over the next {months} {months === 1 ? "month" : "months"}, roughly how
        does it split? Edit freely — the total follows your numbers.
      </p>
      <div className="mt-4 grid max-w-2xl gap-x-8 gap-y-2.5 sm:grid-cols-2">
        {SPLIT_CATEGORIES.map((c) => (
          <div key={c.slug} className="flex items-center justify-between gap-3">
            <label
              htmlFor={`split-${c.slug}`}
              className="text-[15px] font-normal text-foreground/90"
            >
              {c.label}
            </label>
            <div className="flex items-center gap-1.5">
              <span className="text-[15px] text-muted-foreground">₹</span>
              <Input
                id={`split-${c.slug}`}
                type="number"
                min={0}
                step={5000}
                value={values[c.slug] ?? ""}
                onChange={(e) => {
                  // min={0} only clamps the spinner — a typed "-5000" gets
                  // through, silently counting as ₹0. Normalize it visibly.
                  const raw = e.target.value;
                  onChange(c.slug, Number(raw) < 0 ? "0" : raw);
                }}
                className="h-10 w-32 bg-input/30 text-right text-[15px]! tabular-nums"
              />
            </div>
          </div>
        ))}
      </div>
      {/* Categories win: the total is DERIVED from the rows (decision 7) —
          no "must equal your earlier number" validation, ever. */}
      <p className="mt-4 text-sm tabular-nums text-muted-foreground">
        Total ₹{total.toLocaleString("en-IN")} over {months}{" "}
        {months === 1 ? "month" : "months"}
        {total > 0 && <> — ≈ ₹{monthly.toLocaleString("en-IN")}/month</>}
      </p>
      <Button
        onClick={onBuild}
        disabled={building}
        size="lg"
        className="mt-5 bg-gold text-gold-foreground hover:bg-gold/90 disabled:opacity-60"
      >
        Build my card strategy
        <ArrowRight />
      </Button>
    </div>
  );
}
