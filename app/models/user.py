from datetime import datetime

from sqlalchemy import Column, UniqueConstraint
from sqlalchemy import DateTime as SADateTime
from sqlalchemy.dialects.postgresql import CITEXT
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "users_user"
    # Django's unique=True on email creates a named UNIQUE CONSTRAINT
    # (whose backing index serves lookups too), not a separate unique
    # index -- declaring it this way instead of Column(unique=True,
    # index=True) avoids Alembic seeing two different-shaped objects
    # (a constraint it thinks should be removed, plus an index it thinks
    # should be added) for what's actually the same thing.
    __table_args__ = (UniqueConstraint("email", name="users_user_email_key"),)

    id: int | None = Field(default=None, primary_key=True)
    password: str = Field(max_length=128)
    # timestamp with time zone in the live schema, nullable.
    last_login: datetime | None = Field(
        default=None, sa_column=Column(SADateTime(timezone=True))
    )
    is_superuser: bool = False
    email: str = Field(sa_column=Column(CITEXT, nullable=False))
    is_email_verified: bool = False
    is_active: bool = True
    # timestamp with time zone in the live schema, NOT NULL, no server
    # default -- always set explicitly on create.
    date_joined: datetime = Field(sa_column=Column(SADateTime(timezone=True), nullable=False))
    new_email: str = Field(
        default="", sa_column=Column(CITEXT, nullable=False, server_default="")
    )
    is_new_email_confirmed: bool = False
    first_name: str = Field(max_length=100, default="")
    last_name: str = Field(max_length=100, default="")

    @property
    def is_staff(self) -> bool:
        # Not a column in Django either -- a Python property (is_staff ==
        # is_superuser). Never persist this.
        return self.is_superuser
