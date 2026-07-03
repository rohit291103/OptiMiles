# Seed data — the highest-review-bar artifact in the repo

Catalog data lands here as human-reviewable YAML in build-plan Phase 1
(backend-build-plan-v1 §6). Rules, non-negotiable:

- Every reward rule, ratio, cap, milestone and award-chart row carries
  `source` (bank T&C URL / research doc ref) and `verified_on` (date).
- Re-verify against current bank pages at seed time — the research doc is a
  starting point, not truth.
- `validate_catalog()` runs on snapshot load and in CI.
- Seed PRs get line-by-line human review. A wrong ratio shipped confidently
  is the product's existential failure (PRD risk 8-A).
