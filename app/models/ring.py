from datetime import UTC, datetime

from sqlalchemy import Column
from sqlalchemy import DateTime as SADateTime
from sqlmodel import Field, SQLModel


class RingDevice(SQLModel, table=True):
    __tablename__ = "ring_devices"

    id: int | None = Field(default=None, primary_key=True)
    external_id: str = Field(max_length=100, unique=True)
    name: str = Field(max_length=200)
    battery_life: int | None = Field(default=None)
    last_motion_at: datetime | None = Field(
        default=None, sa_column=Column(SADateTime(timezone=True))
    )


class RingDeviceLog(SQLModel, table=True):
    __tablename__ = "ring_device_logs"

    id: int | None = Field(default=None, primary_key=True)
    device_id: int = Field(foreign_key="ring_devices.id", index=True)
    battery_life: int
    last_motion_at: datetime | None = Field(
        default=None, sa_column=Column(SADateTime(timezone=True))
    )
    recorded_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(SADateTime(timezone=True), nullable=False),
    )
