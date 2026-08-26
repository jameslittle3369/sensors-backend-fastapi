from datetime import UTC, datetime

from sqlalchemy import Column
from sqlalchemy import DateTime as SADateTime
from sqlmodel import Field, SQLModel


class PhotoUvmeter(SQLModel, table=True):
    __tablename__ = "photo_uvmeters"

    external_id: str = Field(max_length=50, primary_key=True)  # rtl_433 sensor id, as str
    name: str = Field(max_length=200)
    # rtl_433's field is literally "lux" -- stored under this name to
    # match the requested model shape, not implying a lux->lumens
    # conversion (same number either way).
    current_lumens: int | None = Field(default=None)
    current_uv_index: int | None = Field(default=None)


class PhotoUvmeterLog(SQLModel, table=True):
    __tablename__ = "photo_uvmeter_logs"

    id: int | None = Field(default=None, primary_key=True)
    photo_uvmeter_id: str = Field(
        foreign_key="photo_uvmeters.external_id", max_length=50, index=True
    )
    lumens: int
    uv_index: int
    recorded_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(SADateTime(timezone=True), nullable=False, index=True),
    )
