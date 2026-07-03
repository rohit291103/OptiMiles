# OptiMiles backend

Read `docs/architecture/backend-build-plan-v1.md` before touching this tree —
it locks the module boundaries, build order, and schema.

## Run

```sh
uv sync                    # install deps (creates .venv)
uv run uvicorn app.main:app --reload   # http://127.0.0.1:8000/health
```

## Checks (same as CI)

```sh
uv run ruff check . && uv run ruff format --check .
uv run mypy app
uv run pytest
```

## Migrations

```sh
cp .env.example .env       # set DATABASE_URL to your Supabase project
uv run alembic upgrade head
```

The initial migration targets a fresh **Supabase** project (`auth.users` FK +
`auth.uid()` RLS policies).
