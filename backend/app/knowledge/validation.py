"""validate_catalog() — the invariants a trustworthy catalog must satisfy
(build plan §6). Runs on snapshot load and in CI. Bad reference data fails
loudly and completely (all issues at once), never as silent zeros downstream.
"""

from fractions import Fraction

from app.domain import CatalogSnapshot, SpendCategory

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
