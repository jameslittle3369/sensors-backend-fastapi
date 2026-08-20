from datetime import datetime

from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy import DateTime as SADateTime
from sqlmodel import Field, SQLModel


class Token(SQLModel, table=True):
    __tablename__ = "authtoken_token"

    key: str = Field(max_length=40, primary_key=True)
    # timestamp with time zone in the live schema.
    created: datetime = Field(sa_column=Column(SADateTime(timezone=True), nullable=False))
    user_id: int = Field(
        sa_column=Column(Integer, ForeignKey("users_user.id"), unique=True, nullable=False)
    )
