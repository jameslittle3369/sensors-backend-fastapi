from datetime import UTC, datetime

from sqlalchemy import Column
from sqlalchemy import DateTime as SADateTime
from sqlmodel import Field, SQLModel


class IkeaDevice(SQLModel, table=True):
    __tablename__ = "ikea_devices"

    id: int | None = Field(default=None, primary_key=True)
    external_id: str = Field(max_length=100, unique=True)
    name: str = Field(max_length=200)
    battery_pct: int | None = Field(default=None)
    last_seen_at: datetime | None = Field(
        default=None, sa_column=Column(SADateTime(timezone=True))
    )


class IkeaDeviceLog(SQLModel, table=True):
    __tablename__ = "ikea_device_logs"

    id: int | None = Field(default=None, primary_key=True)
    device_id: int = Field(foreign_key="ikea_devices.id", index=True)
    battery_pct: int
    recorded_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(SADateTime(timezone=True), nullable=False),
    )
