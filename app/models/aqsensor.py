from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import Column
from sqlalchemy import DateTime as SADateTime
from sqlmodel import Field, SQLModel


class AQSensor(SQLModel, table=True):
    __tablename__ = "aqsensors_aqsensor"

    id: int | None = Field(default=None, primary_key=True)
    name: str | None = Field(max_length=100, default=None)


class AQLog(SQLModel, table=True):
    __tablename__ = "aqsensors_aqlog"

    id: int | None = Field(default=None, primary_key=True)
    aq_sensor_id: int = Field(foreign_key="aqsensors_aqsensor.id")
    # timestamp with time zone in the live schema.
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(SADateTime(timezone=True)),
    )
    # Plain string, NOT a Python Enum: the declared Django choices are
    # Temp, HUM, PM25, PM10, PM25R, PM10R, VOC, NO2, but the actual
    # ingestion code (apps/api/v1/tstats/views.py::get_aq_sensor) writes
    # 'VOC', 'NO2', 'P25R', 'P10R', 'PM25', 'PM10', 'HUMIDITY', 'TEMP' --
    # four of which (P25R, P10R, HUMIDITY, TEMP) don't match the declared
    # choices at all. Django's choices= isn't DB-enforced, so this has
    # been silently writing values outside the nominal choice set. A real
    # Enum column would reject inserts that currently succeed, so this
    # stays a plain string to preserve bug-for-bug write compatibility.
    measurement: str = Field(max_length=20)
    value: Decimal = Field(max_digits=10, decimal_places=1)
