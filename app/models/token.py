from datetime import datetime

from sqlalchemy import Column, ForeignKey, Index, Integer
from sqlalchemy import DateTime as SADateTime
from sqlmodel import Field, SQLModel


class Token(SQLModel, table=True):
    __tablename__ = "authtoken_token"
    # Django adds a varchar_pattern_ops index alongside the PK's own
    # btree index -- SQLAlchemy doesn't create this automatically, named
    # to match Django's exact index name so Alembic sees no diff.
    __table_args__ = (
        Index(
            "authtoken_token_key_10f0b77e_like",
            "key",
            postgresql_ops={"key": "varchar_pattern_ops"},
        ),
    )

    key: str = Field(max_length=40, primary_key=True)
    # timestamp with time zone in the live schema.
    created: datetime = Field(sa_column=Column(SADateTime(timezone=True), nullable=False))
    # Django's Token.user is a OneToOneField, which normally implies a
    # unique constraint on user_id -- but the live schema (verified via
    # \d+ authtoken_token) has no such constraint, just the FK. Matching
    # reality rather than what the Django model "should" imply. The FK
    # itself is DEFERRABLE INITIALLY DEFERRED in the live schema (Django's
    # Postgres backend's default for this version) -- replicated here so
    # Alembic doesn't think the constraint needs to be dropped/recreated.
    user_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("users_user.id", deferrable=True, initially="DEFERRED"),
            nullable=False,
        )
    )
