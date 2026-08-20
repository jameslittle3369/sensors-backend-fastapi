from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import Column, Index
from sqlalchemy import DateTime as SADateTime
from sqlmodel import Field, SQLModel


class AQSensor(SQLModel, table=True):
    __tablename__ = "aqsensors_aqsensor"

    id: int | None = Field(default=None, primary_key=True)
    name: str | None = Field(max_length=100, default=None)


class AQLog(SQLModel, table=True):
    __tablename__ = "aqsensors_aqlog"
    # Matches Django's exact index name rather than Field(index=True),
    # which would generate a differently-named index and show up as a
    # permanent no-op diff in `alembic check`. Integer column, so no
    # varchar_pattern_ops variant needed (that's text-only).
    __table_args__ = (Index("aqsensors_aqlog_aq_sensor_id_6184f7dd", "aq_sensor_id"),)

    id: int | None = Field(default=None, primary_key=True)
    # NOT a real DB-level FK constraint -- verified via \d+
    # aqsensors_aqlog, only a plain index exists
    # (aqsensors_aqlog_aq_sensor_id_6184f7dd), no "Foreign-key
    # constraints:" section. Same deliberate-drop-for-performance
    # pattern as the tstats log tables.
    aq_sensor_id: int
    # timestamp with time zone in the live schema, NOT NULL.
    # nullable=False must be explicit here, see
    # TstatLog.created_at's comment for why.
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(SADateTime(timezone=True), nullable=False),
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
