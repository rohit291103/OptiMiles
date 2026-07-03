# Decision Log — Phase 1: Knowledge Engine + Seed Catalog (modeling calls)

**Date:** 2026-07-04
**Area:** backend / data

## Context

Build-plan Phase 1 (Knowledge Engine) was implemented test-first: seed catalog
for all 8 MVP cards, `validate_catalog()`, snapshot loading (YAML + DB paths),
goal resolution (Stage 2) and requirement estimation (Stage 3). Writing the
seeds forced several modeling decisions the build plan had left open, and the
research doc (`docs/research/singapore_airlines_krisflyer_indian_credit_card_research_v1.md`)
turned out to cover only ~6 of 8 cards and no award-chart or category-level
earn data — so a seeding policy for unverified values was needed.

## Decisions

1. **HDFC is modeled as TWO reward currencies** (`hdfc-rp-premium` for
   Infinia/Diners Black at 1:1 KrisFlyer; `hdfc-rp-regalia` for Regalia Gold
   at 2:1, flagged needs-verification). Rationale: the transfer *entitlement*
   differs by card tier, and a currency in schema v1.1 means "a points pool
   with one transfer entitlement." This is the anticipated alternative to the
   card-level override column (build plan §3.3), which stays deferred until a
   same-pool-different-ratio case is validated. D-1's dedupe win survives:
   Infinia + DCB still share one currency and one link row.
2. **Seeding policy — conservative and explicitly provenance-tagged.** Every
   row carries `source` + `verified_on`; rows seeded from market knowledge
   rather than the research doc additionally carry `needs_verification: true`
   (the open review queue is `grep -rn "needs_verification: true" seeds/catalog`).
   Earn rates: every card gets a `default` category at base rate; accelerated
   categories only where documented (SmartBuy 5X seeded, not the headline
   10X) so projections under-promise. Where the research doc and db-schema-v1's
   illustrative examples conflict (Infinia 1:1 vs the old 2:1 example), **the
   research doc wins** — golden tests pin the research values.
3. **Maharaja Club is deliberately sparse:** partner row + one
   needs-verification HDFC link, NO award-chart rows. Absent data fails
   honestly as an explicit `UnsupportedRoute`; wrong data lies. Expanding
   Maharaja Club coverage is tracked as next-up work, not silently missing.
4. **Snapshot version = content hash over domain objects** (`cat-<sha12>`),
   not file bytes or DB timestamps — the same catalog content yields the same
   version whether loaded from YAML or from Postgres. Proven by the seed
   script's round-trip check (seed version == DB-reload version,
   `cat-ee2d1c3701e4` as of this entry). This supersedes the build plan's
   "max updated_at" MVP suggestion for D-2 lineage — strictly stronger, still
   zero infrastructure.
8. **Phase-exit reviewer findings, all fixed same-day:** (a) ambiguous
   program hints ("air" matches both partners) now return a
   ClarificationRequest instead of silently picking the first match — a
   dormant Stage-2 trust bug that would have fired when Maharaja Club gains
   chart rows; (b) `store.py` catalog SELECTs gained `ORDER BY id` (Postgres
   row order is undefined) and the load script's round-trip check became
   order-independent (sorted per-table content + version equality); (c) the
   version hash normalizes Decimals (3.33 == 3.330) so a NUMERIC column
   can't shift the version; (d) duplicate (card, category) pairs now fail
   `validate_catalog()` loudly instead of surfacing at DB insert. Each fix
   carries a regression test (44 tests total).
5. **Deterministic identities:** every seeded row's UUID is UUID5 of
   `kind:slug` under an OptiMiles namespace — idempotent DB upserts, stable
   fixtures, and seed-file diffs that map 1:1 to DB diffs. Catalog sync
   **deactivates** (never deletes) rows removed from seeds, since user goals
   lock historical award-chart ids.
6. **Provenance lives in YAML, not the DB.** The reviewed seed files are the
   audit artifact; DB rows link back via deterministic ids. No schema change
   for source/verified_on columns.
7. **Stage 2/3 behavior locked by tests:** unknown city → ClarificationRequest
   (never a guessed region); route without a chart row → UnsupportedRoute
   with the supported alternatives (never an estimate); requirement buffer
   rounds UP; missing locked chart row raises loudly (`ChartRowMissing`).
   MVP award type is saver-only at resolution time.

## Not done (deferred)

- **Human verification of `needs_verification: true` rows** — the user must
  check ~60% of seed rows against live bank/KrisFlyer pages (all award-chart
  values, Regalia/HSBC/Atlas/Magnus/Amex card details). The catalog is
  load-bearing but NOT yet trustworthy for real users.
- **Standard Magnus Group A annual transfer cap** — research doc confirms a
  cap exists but gives no figure; link seeded uncapped + flagged.
- **Maharaja Club award charts + remaining links** — after KrisFlyer path is
  end-to-end.
- **`/health` catalog_snapshot_version** stays null until the pipeline phase
  wires a DB-backed snapshot into the API lifecycle.
- **Stale-chart warning path** (locked chart row deactivated in a newer
  snapshot) — needs two snapshot generations in play; pipeline-phase concern.
