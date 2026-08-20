from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import Column
from sqlalchemy import DateTime as SADateTime
from sqlmodel import Field, SQLModel


class Thermometer(SQLModel, table=True):
    __tablename__ = "tstats_thermometer"

    # Natural string primary key (a 1-Wire ROM ID), not autoincrement.
    romid: str = Field(max_length=50, primary_key=True)
    pretty_name: str = Field(max_length=50)
    current: Decimal = Field(default=0, max_digits=8, decimal_places=4)
    high_24_hour: Decimal = Field(default=0, max_digits=8, decimal_places=4)
    low_24_hour: Decimal = Field(default=0, max_digits=8, decimal_places=4)


class TstatLog(SQLModel, table=True):
    __tablename__ = "tstats_tstatlog"

    id: int | None = Field(default=None, primary_key=True)
    # Django's FK field was literally named "romid" (a ForeignKey to
    # Thermometer), so the DB column is romid_id.
    romid_id: str = Field(foreign_key="tstats_thermometer.romid", max_length=50)
    primary_value: Decimal = Field(max_digits=8, decimal_places=4)
    # Live schema (verified via \d+ tstats_tstatlog) is `timestamp with
    # time zone` -- Django's naive default=datetime.now was converted to
    # aware UTC on save because USE_TZ=True. Keep this tz-aware.
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(SADateTime(timezone=True)),
    )

    @property
    def degrees_farenheit(self) -> Decimal:
        return (self.primary_value * 9) / 5 + 32
