from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import Column, Index
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
    # Django adds a varchar_pattern_ops index alongside the PK's own
    # btree index -- SQLAlchemy doesn't create this automatically, named
    # to match Django's exact index name so Alembic sees no diff.
    __table_args__ = (
        Index(
            "tstats_thermohygrometer_id_channel_5a332268_like",
            "id_channel",
            postgresql_ops={"id_channel": "varchar_pattern_ops"},
        ),
    )

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
    # Matches Django's exact index names (plain btree + varchar_pattern_ops
    # variant) rather than Field(index=True), which would generate a
    # differently-named index and show up as a permanent no-op diff.
    __table_args__ = (
        Index("tstats_thermohygrostatlog_romid_id_98e9487c", "thermohygrometer_id"),
        Index(
            "tstats_thermohygrostatlog_romid_id_98e9487c_like",
            "thermohygrometer_id",
            postgresql_ops={"thermohygrometer_id": "varchar_pattern_ops"},
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    # FK field was renamed from "romid" to "thermohygrometer" via Django
    # migration 0006_auto_20210212_2023.py -- DB column is
    # thermohygrometer_id. NOT a real DB-level FK constraint though --
    # verified via \d+ tstats_thermohygrostatlog, only plain indexes
    # exist, same deliberate-drop-for-performance pattern as
    # tstats_tstatlog.romid_id.
    thermohygrometer_id: str = Field(max_length=50)
    temp_f: Decimal = Field(max_digits=8, decimal_places=4)
    humidity: Decimal = Field(max_digits=8, decimal_places=1)
    # timestamp with time zone in the live schema, NOT NULL (Django's
    # USE_TZ=True converts the naive datetime.now() default to aware UTC
    # before storage) -- keep this tz-aware. nullable=False must be
    # explicit here, see TstatLog.created_at's comment for why.
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(SADateTime(timezone=True), nullable=False),
    )
