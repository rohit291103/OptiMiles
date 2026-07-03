# Seed data — the highest-review-bar artifact in the repo

The MVP catalog lives in `catalog/*.yaml` (currencies, partners,
transfer_links, cards incl. categories + milestones, award_charts).

- **Load into the DB:** `uv run python seeds/load_to_db.py` — validates,
  upserts (deterministic UUID5 ids ⇒ idempotent), deactivates rows removed
  from the seeds, then proves the round-trip: the DB-loaded snapshot's
  content-hash version must equal the seeds'.
- **Provenance stays here, not in the DB:** `source` / `verified_on` /
  `needs_verification` are reviewed in these files; DB rows link back via
  their deterministic ids.
- **`needs_verification: true`** marks values seeded from general market
  knowledge rather than the research doc — they MUST be human-verified
  against the bank's current pages before the catalog is treated as
  trustworthy. `grep -rn "needs_verification: true" catalog/` lists the open
  review queue.

Rules, non-negotiable (backend-build-plan-v1 §6):

- Every reward rule, ratio, cap, milestone and award-chart row carries
  `source` (bank T&C URL / research doc ref) and `verified_on` (date).
- Re-verify against current bank pages at seed time — the research doc is a
  starting point, not truth.
- `validate_catalog()` runs on snapshot load and in CI (the seed tests load
  the real files).
- Seed PRs get line-by-line human review. A wrong ratio shipped confidently
  is the product's existential failure (PRD risk 8-A).
