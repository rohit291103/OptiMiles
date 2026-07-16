"use client";

import type { CardEducation, EducationPayload, EducationTransferLink } from "@/lib/api";

/**
 * The wizard's education step (decision 4/13, slice 6): the selected wallet's
 * reward story — cards → partners → reward system — rendered as deterministic
 * template text straight from the catalog payload. Every number here is a
 * catalog fact (earn rates, caps, transfer ratios, fees, processing days);
 * LLM framing lands on top later (slice 10) and can never block this render.
 */
export function EducationStory({
  payload,
  narrative,
}: {
  payload: EducationPayload;
  /** Optional LLM-phrased framing (decision 10) — lands on top when it
   * arrives; the deterministic story below never waits for it. */
  narrative?: string | null;
}) {
  const cardNameOf = new Map(payload.cards.map((c) => [c.card_id, c.card_name]));

  return (
    <div className="mt-4 space-y-5">
      {narrative && (
        <p className="max-w-2xl border-l-2 border-gold/40 pl-4 text-base leading-relaxed text-foreground/85">
          {narrative}
        </p>
      )}
      {/* The shared-ecosystem insight first — it's the "aha" the step exists
          to teach (e.g. Atlas AND TravelOne both feed KrisFlyer). */}
      {payload.shared_partners.map((partner) => (
        <div
          key={partner.partner_id}
          className="rounded-xl border border-gold/30 bg-gold/5 px-4 py-3 text-base text-foreground"
        >
          <span className="font-medium text-gold">
            {partner.card_ids.length === payload.cards.length
              ? "All of your cards"
              : `${partner.card_ids.length} of your cards`}
          </span>{" "}
          ({partner.card_ids.map((id) => cardNameOf.get(id) ?? "card").join(", ")})
          can move points into <span className="font-medium">{partner.program_name}</span>{" "}
          — they add up toward the same award seat.
        </div>
      ))}

      <div className="grid gap-4 lg:grid-cols-2">
        {payload.cards.map((card) => (
          <CardStory key={card.card_id} card={card} />
        ))}
      </div>
    </div>
  );
}

function CardStory({ card }: { card: CardEducation }) {
  // Show accelerated categories before the default "everything else" rule —
  // the accelerated rates are the story; the default is the floor.
  const rules = [...card.earn_rules].sort((a, b) =>
    a.category_slug === "default" ? 1 : b.category_slug === "default" ? -1 : 0,
  );

  return (
    <section className="rounded-2xl border border-hairline bg-background/40 p-5">
      <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground/80">
        {card.bank}
      </p>
      <h4 className="mt-0.5 font-heading text-xl text-foreground">
        {card.card_name}
      </h4>
      <p className="mt-1 text-sm text-muted-foreground">
        Earns <span className="text-foreground">{card.currency.currency_name}</span>
      </p>

      <div className="mt-4 space-y-1.5">
        <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
          How it earns
        </p>
        <ul className="space-y-1.5">
          {rules.length === 0 && (
            <li className="text-sm text-foreground">
              {formatRate(card.base_earn_rate)} pts per ₹100 on your spending.
            </li>
          )}
          {rules.map((rule) => (
            <li key={rule.category_slug} className="text-sm leading-relaxed text-foreground">
              <span className="text-muted-foreground">{rule.category_label}:</span>{" "}
              <span className="font-medium tabular-nums">
                {formatRate(rule.earn_rate)} pts/₹100
              </span>
              {rule.monthly_cap_inr != null && (
                <span className="text-muted-foreground">
                  {" "}
                  up to ₹{rule.monthly_cap_inr.toLocaleString("en-IN")}/month
                </span>
              )}
            </li>
          ))}
        </ul>
      </div>

      <div className="mt-4 space-y-1.5">
        <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
          Where the points can go
        </p>
        {card.transfer_links.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No airline or hotel transfers — this card&apos;s rewards stay as{" "}
            {card.currency.currency_name}.
          </p>
        ) : (
          <ul className="space-y-1.5">
            {card.transfer_links.map((link) => (
              <TransferLine key={link.partner_id} link={link} />
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

function TransferLine({ link }: { link: EducationTransferLink }) {
  const details: string[] = [];
  if (link.max_transfer_points != null) {
    details.push(`up to ${link.max_transfer_points.toLocaleString("en-IN")} pts/year`);
  }
  if (link.transfer_fee_inr > 0) {
    details.push(`₹${link.transfer_fee_inr.toLocaleString("en-IN")} fee`);
  }
  details.push(
    link.processing_days_max === 0
      ? "instant"
      : `${link.processing_days_min}–${link.processing_days_max} days`,
  );
  return (
    <li className="text-sm leading-relaxed text-foreground">
      → <span className="font-medium">{link.program_name}</span> at{" "}
      <span className="tabular-nums">
        {link.ratio_from}:{link.ratio_to}
      </span>
      <span className="text-muted-foreground"> ({details.join(", ")})</span>
    </li>
  );
}

/** "2.00" → "2", "16.65" → "16.65" — catalog rates are Decimal strings. */
function formatRate(rate: string): string {
  const n = Number(rate);
  return Number.isFinite(n) ? String(n) : rate;
}
