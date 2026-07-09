# Decision Log — Supabase Pooler Compatibility + Catalog RLS

**Date:** 2026-07-06
**Area:** database / infra (connection config + a schema migration on the live DB)

## Context

Wiring the backend to the live Supabase DB (to make signed-in saves persist) surfaced two real issues that had been latent because nothing had connected the app to Supabase over the pooler before.

## Decisions

1. **Connect via the transaction-mode pooler, not the direct host.** The `.env` `DATABASE_URL` was the **direct** connection (`db.<ref>.supabase.co:5432`), which is IPv6-only and unreachable from many local networks — it timed out. Switched to the **transaction pooler** (`postgres.<ref>@aws-0-ap-northeast-1.pooler.supabase.com:6543`), which db-schema §6.5 already prescribed. (Direct-vs-pooler is a per-`.env` value, not committed; the `.env.example` comment should point at the pooler form.)

2. **`statement_cache_size=0` on every asyncpg engine — REQUIRED against the pooler.** Once connected, catalog reads failed with `DuplicatePreparedStatementError`. Supabase's transaction-mode pooler is PgBouncer, which multiplexes many client sessions over few server connections, so asyncpg's per-connection prepared-statement cache collides across sessions. The fix is to disable that cache. Applied in **both** engine-creation sites: `app/api/deps.py` (`get_engine`) and `alembic/env.py` (`run_async_migrations`). This is not a dev-only workaround — it would break **all** DB access in production; it is the documented asyncpg + PgBouncer-transaction-mode requirement.

3. **RLS on the catalog tables with a public read-only policy** (migration `0003_catalog_rls_read_only`). Supabase exposes every `public` table to PostgREST via the anon key, so the 7 catalog tables without RLS were flagged "Critical". The catalog is public reference data (card names, transfer ratios, award charts) — not secret — but D-4 wants RLS on as defense-in-depth. So each catalog table gets `ENABLE ROW LEVEL SECURITY` + a `FOR SELECT USING (true)` policy: reads stay open, and the absence of write policies denies anon/authenticated writes, leaving the service role (which bypasses RLS, and is how `repositories/catalog_admin.py` writes) as the only mutator. The 8 user-scoped tables already had RLS from `0001`; now **every** public table has RLS.

## Verification

- Pooler + `statement_cache_size=0`: `get_snapshot()` loads the catalog from the live DB; `/health` reports a real `catalog_snapshot_version` (was `null`); `/catalog/cards` and `/simulations` return real data end-to-end.
- Migration `0003` applied to the live DB (user-approved — production change): `alembic current` = `0003 (head)`; all 7 catalog tables show `RLS ON` + a `*_public_read` SELECT policy. **After enabling RLS, the backend still reads the catalog and the simulator still returns a recommendation** — confirming the service role bypasses RLS as intended (the risk was RLS silently blocking the app's own reads; it does not).
- 239 backend tests green, mypy strict + ruff clean.

## Not done / follow-ups

- Update `backend/.env.example`'s `DATABASE_URL` comment to show the **pooler** form (`postgres.<ref>@...pooler.supabase.com:6543`), so the direct-connection timeout isn't rediscovered.
- The DB password transited chat during this debugging — rotation recommended when convenient (user has explicitly deferred it).
- A local (non-Supabase) Postgres dev flow would need an `auth` schema stub for the `auth.uid()` policies; still deferred (migrations target Supabase).
