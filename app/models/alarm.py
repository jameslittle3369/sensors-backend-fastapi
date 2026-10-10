from datetime import UTC, datetime

from sqlalchemy import Column
from sqlalchemy import DateTime as SADateTime
from sqlmodel import Field, SQLModel


class AlarmZone(SQLModel, table=True):
    __tablename__ = "alarm_zones"

    external_id: str = Field(max_length=10, primary_key=True)  # DSC zone number, as str
    name: str = Field(max_length=200)
    zone_type: str = Field(max_length=20)  # door, window, motion, smoke, heat, other
    current_open: bool | None = Field(default=None)
    current_fault: bool | None = Field(default=None)
    current_alarm: bool | None = Field(default=None)
    current_tamper: bool | None = Field(default=None)
    current_low_battery: bool | None = Field(default=None)


class AlarmZoneLog(SQLModel, table=True):
    __tablename__ = "alarm_zone_logs"

    id: int | None = Field(default=None, primary_key=True)
    zone_id: str = Field(foreign_key="alarm_zones.external_id", max_length=10, index=True)
    event: str = Field(max_length=20)
    recorded_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(SADateTime(timezone=True), nullable=False, index=True),
    )


class AlarmPartition(SQLModel, table=True):
    __tablename__ = "alarm_partitions"

    external_id: str = Field(max_length=10, primary_key=True)  # DSC partition number, as str
    name: str = Field(max_length=200)
    current_status: str | None = Field(default=None, max_length=20)


class AlarmPartitionLog(SQLModel, table=True):
    __tablename__ = "alarm_partition_logs"

    id: int | None = Field(default=None, primary_key=True)
    partition_id: str = Field(
        foreign_key="alarm_partitions.external_id", max_length=10, index=True
    )
    status: str = Field(max_length=20)
    recorded_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(SADateTime(timezone=True), nullable=False, index=True),
    )


class AlarmTroubleLog(SQLModel, table=True):
    """Panel-wide trouble conditions (AC loss, bell trouble, low battery,
    etc.) -- not tied to a specific zone or partition, so no dimension
    table, just an event log."""

    __tablename__ = "alarm_trouble_logs"

    id: int | None = Field(default=None, primary_key=True)
    condition: str = Field(max_length=30)
    recorded_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(SADateTime(timezone=True), nullable=False, index=True),
    )
