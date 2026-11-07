"use client";

import { Check, Plane } from "lucide-react";

import type { PartnerReach } from "@/lib/api";

const inr = new Intl.NumberFormat("en-IN");

/**
 * "Where do you want these points to go?" — the choice the product must ASK
 * rather than assume.
 *
 * Points across issuers are genuinely incommensurable, so ranking needs a
 * common unit, and a transfer program is the only honest one the catalog
 * supports. That is a reason to ask, not a licence to default: an earlier
 * version silently priced every wallet in KrisFlyer because the (retired) MVP
 * scope named it primary, and printed that program's name to users who had
 * never mentioned it. See `CLAUDE.md` → *Never Assume the User's Goal*.
 *
 * Only programs the user's own wallet can reach are offered. The catalog's
 * partners are not evenly reachable — both Axis currencies reach KrisFlyer
 * and nothing else — so an unfiltered list would be a menu of dead ends.
 *
 * There is deliberately no "whichever is best" option: 333 KrisFlyer miles and
 * 166 Marriott points are no more comparable than the source currencies were,
 * so picking for the user would smuggle the assumption back in.
 */
export function ProgramChooser({
  reach,
  selectedId,
  onSelect,
  prompt,
  showBestRoute = true,
  clearLabel = "Tap again to go back to points.",
  labelFor = (partner: PartnerReach) => partner.program_name,
  hideCount = false,
}: {
  reach: PartnerReach[];
  selectedId: string | null;
  onSelect: (partnerId: string | null) => void;
  prompt: string;
  /** The wallet's best ratio into the chosen program. Best Card turns it off:
   * it shows per-card ratios itself, and one wallet-wide ratio beside a
   * different card's answer reads as a contradiction. */
  showBestRoute?: boolean;
  clearLabel?: string;
  /** How a program is named on its chip (Best Card strips "ALL - "). */
  labelFor?: (partner: PartnerReach) => string;
  /** Hide "via N cards" — unclear where the page already lists the cards. */
  hideCount?: boolean;
}) {
  if (reach.length === 0) {
    return (
      <div className="rounded-2xl border border-hairline bg-input/[0.07] px-5 py-4">
        <p className="text-sm text-muted-foreground">
          None of these cards transfer their rewards anywhere — they&apos;re
          redeemed with the issuer, so there&apos;s no transfer question to ask.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-hairline bg-input/[0.07] px-5 py-4">
      <p className="flex items-center gap-2 text-sm font-semibold text-foreground">
        <Plane className="size-4 text-gold" aria-hidden="true" />
        {prompt}
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        {reach.map((partner) => {
          const selected = partner.partner_id === selectedId;
          return (
            <button
              key={partner.partner_id}
              type="button"
              aria-pressed={selected}
              onClick={() => onSelect(selected ? null : partner.partner_id)}
              className={`flex min-h-11 items-center gap-2 rounded-xl border px-3.5 py-2 text-left text-sm font-medium transition-all sm:min-h-0 ${
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
              <span>
                {labelFor(partner)}
                {hideCount ? null : (
                  <>
                    {" "}
                    <span className="ml-1 text-xs font-normal opacity-70">
                      via {partner.card_ids.length}{" "}
                      {partner.card_ids.length === 1 ? "card" : "cards"}
                    </span>
                  </>
                )}
              </span>
            </button>
          );
        })}
      </div>
      {selectedId ? (
        <p className="mt-3 text-xs text-muted-foreground">
          {showBestRoute ? (
            <>
              Best route from your wallet:{" "}
              {inr.format(
                reach.find((p) => p.partner_id === selectedId)
                  ?.best_miles_per_1000_points ?? 0,
              )}{" "}
              {reach.find((p) => p.partner_id === selectedId)?.partner_type ===
              "hotel"
                ? "points"
                : "miles"}{" "}
              per 1,000 points.{" "}
            </>
          ) : null}
          {clearLabel}
        </p>
      ) : null}
    </div>
  );
}
