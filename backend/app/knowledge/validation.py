"""validate_catalog() — the invariants a trustworthy catalog must satisfy
(build plan §6). Runs on snapshot load and in CI. Bad reference data fails
loudly and completely (all issues at once), never as silent zeros downstream.
"""

from fractions import Fraction
from uuid import UUID

from app.domain import CatalogSnapshot, FeeWaiverKind, ResetAnchor, SpendCategory

# A transfer ratio outside 1:4 … 5:1 is a typo until a human proves otherwise.
_RATIO_BEST = Fraction(1, 4)  # 1 point → 4 miles
_RATIO_WORST = Fraction(5, 1)  # 5 points → 1 mile

_PRIMARY_PROGRAM = "KrisFlyer"
_MVP_BUSINESS_ROUTES = (
    ("India", "Southeast Asia"),
    ("India", "Europe"),
    ("India", "North America"),
)


class CatalogValidationError(Exception):
    def __init__(self, issues: list[str]) -> None:
        self.issues: tuple[str, ...] = tuple(issues)
        super().__init__("catalog validation failed:\n- " + "\n- ".join(issues))


def validate_catalog(snapshot: CatalogSnapshot) -> None:
    issues: list[str] = []

    currency_by_id = {c.id: c for c in snapshot.currencies}
    partner_by_id = {p.id: p for p in snapshot.partners}
    card_by_id = {c.id: c for c in snapshot.cards}

    # ── Referential integrity (orphans) ──────────────────────────────────
    for card in snapshot.cards:
        if card.reward_currency_id not in currency_by_id:
            issues.append(f"orphan FK: card '{card.card_name}' references unknown currency")
    for link in snapshot.transfer_links:
        if link.currency_id not in currency_by_id:
            issues.append(f"orphan FK: transfer link {link.id} references unknown currency")
        if link.partner_id not in partner_by_id:
            issues.append(f"orphan FK: transfer link {link.id} references unknown partner")
    for rule in snapshot.category_rules:
        if rule.card_id not in card_by_id:
            issues.append(f"orphan FK: category rule '{rule.category_label}' has unknown card")
    for milestone in snapshot.milestones:
        if milestone.card_id not in card_by_id:
            issues.append(f"orphan FK: milestone {milestone.id} references unknown card")
        if milestone.valid_from is not None or milestone.valid_until is not None:
            # BR-05/BR-06 (SIM-001): the v1 projector has no calendar anchor
            # and cannot evaluate validity windows. An expired promo silently
            # influencing every projection is worse than refusing the row.
            issues.append(
                f"milestone {milestone.id} carries a validity window "
                "(valid_from/valid_until) — the simulation engine does not enforce "
                "these yet; remove the window or implement BR-05/BR-06 first"
            )
    for chart in snapshot.award_charts:
        if chart.partner_id not in partner_by_id:
            issues.append(f"orphan FK: award chart {chart.id} references unknown partner")

    # ── Lounge access (LA-01 … LA-05) ────────────────────────────────────
    # Lounge conditions are the most perishable rows in the catalog and the
    # most consequential when wrong: a bad condition sends someone to a lounge
    # desk to be turned away, which is precisely the trust failure the product
    # exists to avoid. These rules reject rows that cannot be READ correctly,
    # independently of whether their figures are right.
    program_by_id = {p.id: p for p in snapshot.lounge_programs}
    seen_allowances: dict[tuple[UUID, UUID, str, int | None, str | None], int] = {}
    for access in snapshot.lounge_access:
        if access.card_id not in card_by_id:
            issues.append(f"LA-01 orphan FK: lounge access {access.id} references unknown card")
        if access.program_id not in program_by_id:
            issues.append(
                f"LA-02 orphan FK: lounge access {access.id} references unknown lounge programme"
            )
        # A gate is only actionable as an amount AND a window: "Rs 60,000" on
        # its own tells a cardholder nothing about which period to spend it in.
        if (access.spend_gate_inr is None) != (access.spend_gate_period is None):
            issues.append(
                f"LA-03 lounge access {access.id} has a spend gate missing its amount or "
                "period — both are required, or neither"
            )
        # The user's standing decision (2026-08-26): the reset anchor is seeded
        # per card, never defaulted. Issuers reset on the calendar quarter, the
        # card anniversary and the statement cycle, so a silent assumption is
        # the likeliest source of a wrong visit count.
        if (
            access.visits_per_period is not None
            and access.reset_anchor is ResetAnchor.NOT_APPLICABLE
        ):
            issues.append(
                f"LA-04 lounge access {access.id} counts {access.visits_per_period} visits per "
                f"{access.period} but declares no reset anchor — seed the real anchor "
                "(calendar quarter / card anniversary / statement cycle), never assume one"
            )
        # Two rows for one card+programme+scope only make sense as different
        # spend tiers; otherwise one is a duplicate that would double-count
        # somebody's entitlement.
        key = (
            access.card_id,
            access.program_id,
            str(access.scope),
            access.spend_gate_inr,
            str(access.spend_gate_period) if access.spend_gate_period else None,
        )
        seen_allowances[key] = seen_allowances.get(key, 0) + 1
        if seen_allowances[key] > 1:
            issues.append(
                f"LA-05 duplicate lounge allowance for card {access.card_id} "
                f"({access.scope}, same spend tier) — rows for one scope must differ by "
                "spend gate, or they double-count the entitlement"
            )

    # ── Annual-fee waivers (FW-01 … FW-03) ───────────────────────────────
    # A waiver row is read as progress toward a threshold, so it must be
    # readable completely or not at all: a threshold with no window, or a
    # "no waiver" row that also carries a threshold, is two answers at once.
    waivers_per_card: dict[UUID, int] = {}
    for waiver in snapshot.fee_waivers:
        if waiver.card_id not in card_by_id:
            issues.append(f"FW-01 orphan FK: fee waiver {waiver.id} references unknown card")
        waivers_per_card[waiver.card_id] = waivers_per_card.get(waiver.card_id, 0) + 1
        if waivers_per_card[waiver.card_id] == 2:
            issues.append(
                f"FW-02 card {waiver.card_id} has more than one fee waiver — one card, "
                "one answer (mirrors DB uq_card_fee_waiver)"
            )
        terms = (waiver.threshold_inr, waiver.threshold_comparison, waiver.window_kind)
        if waiver.kind is FeeWaiverKind.SPEND_BASED:
            if any(term is None for term in terms):
                issues.append(
                    f"FW-03 spend-based fee waiver {waiver.id} must state its threshold, "
                    "whether the threshold itself counts, and the window it is measured over"
                )
            if not (waiver.waives_renewal_fee or waiver.waives_joining_fee):
                issues.append(f"FW-03 spend-based fee waiver {waiver.id} waives no fee")
        elif (
            any(term is not None for term in terms)
            or waiver.waives_renewal_fee
            or waiver.waives_joining_fee
            or waiver.excluded_categories
            or waiver.unmodelled_exclusions
        ):
            issues.append(
                f"FW-03 'no waiver' row {waiver.id} carries waiver terms — a card either "
                "has a waiver or it does not"
            )

    # ── Cap overflow (CR-01, CR-02 — decision log 2026-11-02-cap-overflow-earn) ─
    # What spend ABOVE a cap earns differs by issuer (Atlas: base rate; SBI
    # Cashback: nothing). It used to be assumed as base for every cap, which
    # overstated SBI. A capped rule must state it; an uncapped one must not.
    for rule in snapshot.category_rules:
        capped = (
            rule.monthly_cap_inr is not None
            or rule.quarterly_cap_inr is not None
            or rule.annual_cap_inr is not None
        )
        if capped and rule.over_cap_earn is None:
            issues.append(
                f"CR-01 category rule '{rule.category_label}' ({rule.id}) is capped but does "
                "not state over_cap_earn — seed what spend above the cap earns (base_rate "
                "or nothing) from the issuer's terms, never assume it"
            )
        if rule.quarterly_cap_inr is not None or rule.annual_cap_inr is not None:
            # Best Card, Stage 5 and the projector meter MONTHLY caps only; a
            # quarterly/annual cap would be ignored by the blend and earn
            # uncapped. Refuse it until an engine actually meters the period.
            issues.append(
                f"CR-03 category rule '{rule.category_label}' ({rule.id}) carries a "
                "quarterly/annual cap — only monthly caps are metered; seed it as a "
                "monthly cap or implement the period first"
            )
        if not capped and rule.over_cap_earn is not None:
            issues.append(
                f"CR-02 category rule '{rule.category_label}' ({rule.id}) states over_cap_earn "
                "but has no cap — either the cap is missing or the value is a mistake"
            )

    # ── Portal-gated bonus rates (CR-04 — decision log 2026-11-07) ─────────
    # `requires_portal` gates a BONUS: booked direct, the purchase earns the
    # base rate instead. On a rule that is not above base there is nothing to
    # gate, and Best Card would price a phantom 'booked direct' alternative.
    base_by_card = {card.id: card.base_earn_rate for card in snapshot.cards}
    for rule in snapshot.category_rules:
        if rule.requires_portal is None:
            continue
        if not rule.requires_portal.strip():
            issues.append(
                f"CR-04 category rule '{rule.category_label}' ({rule.id}) has a blank "
                "requires_portal — name the portal or leave it null"
            )
        base = base_by_card.get(rule.card_id)
        if base is not None and rule.earn_rate <= base:
            issues.append(
                f"CR-04 category rule '{rule.category_label}' ({rule.id}) names a portal "
                "but is not a bonus rate (earn_rate <= the card's base) — only a bonus "
                "can depend on how you book"
            )

    # ── Card completeness ─────────────────────────────────────────────────
    for card in snapshot.cards:
        card_slugs = [r.category_slug for r in snapshot.category_rules if r.card_id == card.id]
        slugs = set(card_slugs)
        if not slugs:
            issues.append(f"card '{card.card_name}' has no reward categories")
        elif SpendCategory.DEFAULT not in slugs:
            issues.append(f"card '{card.card_name}' lacks a default reward category")
        if len(card_slugs) != len(slugs):
            issues.append(
                f"card '{card.card_name}' has duplicate category slugs "
                "(mirrors DB uq_card_category — fail here, not at DB insert)"
            )

    # ── Transfer-link sanity ──────────────────────────────────────────────
    for link in snapshot.transfer_links:
        ratio = Fraction(link.ratio_from, link.ratio_to)
        if not (_RATIO_BEST <= ratio <= _RATIO_WORST):
            currency = currency_by_id.get(link.currency_id)
            name = currency.currency_name if currency else str(link.currency_id)
            issues.append(
                f"implausible transfer ratio {link.ratio_from}:{link.ratio_to} on '{name}' "
                "(sane bounds 1:4 … 5:1) — verify before seeding"
            )
        if link.processing_days_min > link.processing_days_max:
            issues.append(f"transfer link {link.id}: processing_days_min > max")

    # ── The deliberate negative case ──────────────────────────────────────
    for currency in snapshot.currencies:
        if "cashback" in currency.currency_name.lower() and any(
            link.currency_id == currency.id for link in snapshot.transfer_links
        ):
            issues.append(
                f"Cashback currency '{currency.currency_name}' must have zero transfer links "
                "(it is the deliberate negative case)"
            )

    # ── Primary-program reach + MVP route coverage ────────────────────────
    primary = next((p for p in snapshot.partners if p.program_name == _PRIMARY_PROGRAM), None)
    if primary is None:
        issues.append(f"primary program {_PRIMARY_PROGRAM} missing from partners")
    else:
        if not any(link.partner_id == primary.id for link in snapshot.transfer_links):
            issues.append(f"no currency reaches {_PRIMARY_PROGRAM} — catalog is useless")
        covered = {
            (c.origin_region, c.destination_region)
            for c in snapshot.award_charts
            if c.partner_id == primary.id and c.cabin_class == "business"
        }
        for origin, destination in _MVP_BUSINESS_ROUTES:
            if (origin, destination) not in covered:
                issues.append(
                    f"award chart missing MVP route {origin} → {destination} (business, "
                    f"{_PRIMARY_PROGRAM})"
                )

    if issues:
        raise CatalogValidationError(issues)
