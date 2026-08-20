from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import Column
from sqlalchemy import DateTime as SADateTime
from sqlmodel import Field, SQLModel

# Verified against the live rpi4-db `api` database (`\d+
# tstats_thermohygrometer`): `model` (varchar(50), NOT NULL, no server
# default) and `model_id` (integer, nullable) DO exist, despite not
# appearing in any Django migration file (0001-0006) -- models.py had
# drifted from migration history, but the live schema is ground truth
# and it has these columns.


class ThermoHygrometer(SQLModel, table=True):
    __tablename__ = "tstats_thermohygrometer"

    # Natural string primary key (a sensor channel id), not autoincrement.
    id_channel: str = Field(max_length=50, primary_key=True)
    pretty_name: str = Field(max_length=50)
    current_f: Decimal = Field(default=0, max_digits=8, decimal_places=4)
    high_f_24_hour: Decimal = Field(default=0, max_digits=8, decimal_places=4)
    low_f_24_hour: Decimal = Field(default=0, max_digits=8, decimal_places=4)
    current_h: Decimal = Field(default=0, max_digits=8, decimal_places=4)
    high_h_24_hour: Decimal = Field(default=0, max_digits=8, decimal_places=4)
    low_h_24_hour: Decimal = Field(default=0, max_digits=8, decimal_places=4)
    model: str = Field(max_length=50, default="")
    model_id: int | None = Field(default=None)


class ThermoHygrostatLog(SQLModel, table=True):
    __tablename__ = "tstats_thermohygrostatlog"

    id: int | None = Field(default=None, primary_key=True)
    # FK field was renamed from "romid" to "thermohygrometer" via Django
    # migration 0006_auto_20210212_2023.py -- DB column is
    # thermohygrometer_id.
    thermohygrometer_id: str = Field(
        foreign_key="tstats_thermohygrometer.id_channel", max_length=50
    )
    temp_f: Decimal = Field(max_digits=8, decimal_places=4)
    humidity: Decimal = Field(max_digits=8, decimal_places=1)
    # timestamp with time zone in the live schema (Django's USE_TZ=True
    # converts the naive datetime.now() default to aware UTC before
    # storage) -- keep this tz-aware, don't use naive datetimes.
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(SADateTime(timezone=True)),
    )
