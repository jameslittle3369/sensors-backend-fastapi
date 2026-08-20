"""baseline (no-op)

Represents "schema as of Alembic adoption" for a database that already
existed (restored from the Django-managed tstats-backend-django backup).
Does NOT create any tables -- run `alembic stamp head` against the real
database to mark this as applied without executing any DDL. All *future*
schema changes get real upgrade()/downgrade() bodies via normal
`alembic revision --autogenerate`.

Revision ID: 0001_baseline_noop
Revises:
Create Date: 2026-08-19
"""

from collections.abc import Sequence

revision: str = "0001_baseline_noop"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
