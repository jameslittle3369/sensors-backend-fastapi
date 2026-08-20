# sensors-backend-fastapi

FastAPI replacement for `tstats-backend-django`, reading/writing the same
Postgres schema (already restored on rpi4-db) rather than recreating it.
See `/Users/jl/.claude/plans/in-this-lillittlesensors-project-gentle-cherny.md`
for the full migration plan and scope decisions.

Scope covered so far: users + core auth (login, register, /users/me,
update, change-password, confirm-email) and all IoT resources
(thermometers, thermohygrometers, aqsensors, cameras, /v1/stats, and the
tstats POST ingestion endpoint) -- including several legacy bugs ported
deliberately as-is (see comments at each call site). Social OAuth,
referrals, forgot/change-email, and Django admin are out of scope for
this migration.

## Setup

```bash
uv sync
cp .env.example .env   # fill in real values
```

## Running

```bash
uv run uvicorn app.main:app --reload
```

## Database migrations (Alembic)

The schema already exists (created by Django's migrations, restored from
backup) -- Alembic's first revision (`0001_baseline_noop`) is a
deliberate no-op. On a **fresh** database that already has the real
schema (i.e. rpi4-db), mark it as baselined without running any DDL:

```bash
uv run alembic stamp head
```

All *future* schema changes get real migrations the normal way:

```bash
uv run alembic revision --autogenerate -m "..."
uv run alembic upgrade head
```

Sanity check after stamping: confirm the SQLModel model definitions
produce zero diff against the live schema (if there's a diff, the models
are wrong, not the database):

```bash
uv run alembic check
```

## Tests

Needs a scratch Postgres database with the `citext` extension enabled
(kept entirely separate from the real `api` database):

```bash
createdb sensors_test
psql sensors_test -c 'CREATE EXTENSION citext'
TEST_DATABASE_URL=postgresql+psycopg://$(whoami)@localhost/sensors_test \
  DATABASE_URL=postgresql://$(whoami)@localhost/sensors_test \
  SECRET_KEY=test \
  uv run pytest
```
