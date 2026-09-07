from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import Column
from sqlalchemy import DateTime as SADateTime
from sqlmodel import Field, SQLModel


class Spa(SQLModel, table=True):
    __tablename__ = "spas"

    external_id: str = Field(max_length=50, primary_key=True)  # pybalboa mac_address
    name: str = Field(max_length=200)


class SpaLog(SQLModel, table=True):
    """17 fields, matching hvac_zone_logs' field count -- no per-field
    pruning history yet (unlike hvac's 53->17), this is the initial set:
    everything balboa_spa.py's pybalboa client currently reads. Expect to
    prune later the same way, once real logged data shows what's actually
    useful for this specific spa's equipment configuration."""

    __tablename__ = "spa_logs"

    id: int | None = Field(default=None, primary_key=True)
    spa_id: str = Field(foreign_key="spas.external_id", max_length=50, index=True)
    recorded_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(SADateTime(timezone=True), nullable=False, index=True),
    )

    water_temp_f: Decimal | None = Field(default=None, max_digits=5, decimal_places=1)
    setpoint_f: Decimal | None = Field(default=None, max_digits=5, decimal_places=1)
    # Stored as pybalboa's HeatState/HeatMode/LowHighRange enum .name (e.g.
    # "HEATING"), not the raw int -- readable directly in Grafana/psql with
    # no CASE/join needed, same convention as hvac_zone_logs' system_switch_position.
    heat_state: str | None = Field(default=None, max_length=20)
    heat_mode: str | None = Field(default=None, max_length=20)
    temperature_range: str | None = Field(default=None, max_length=20)

    # Equipment state, each a SpaControl's state .name (e.g. "HIGH", "OFF").
    # Slot counts match balboa_spa.py's PUMP_SLOTS/BLOWER_SLOTS/etc -- an
    # unused slot on spas with fewer pumps/lights/etc than the slot count
    # just logs null.
    pump1_state: str | None = Field(default=None, max_length=20)
    pump2_state: str | None = Field(default=None, max_length=20)
    pump3_state: str | None = Field(default=None, max_length=20)
    pump4_state: str | None = Field(default=None, max_length=20)
    circulation_pump_state: str | None = Field(default=None, max_length=20)
    blower1_state: str | None = Field(default=None, max_length=20)
    blower2_state: str | None = Field(default=None, max_length=20)
    light1_state: str | None = Field(default=None, max_length=20)
    light2_state: str | None = Field(default=None, max_length=20)
    mister_state: str | None = Field(default=None, max_length=20)
    aux1_state: str | None = Field(default=None, max_length=20)
    aux2_state: str | None = Field(default=None, max_length=20)


# Field names shared between SpaLogRequest and SpaLog that participate in
# dedup comparison (everything except identity/bookkeeping columns) --
# kept here so the router shares one source of truth for "what counts as
# a metric," same convention as HVAC_ZONE_LOG_METRIC_FIELDS. Must stay in
# sync (by field name) with balboa_spa.py's METRIC_FIELDS.
SPA_LOG_METRIC_FIELDS: tuple[str, ...] = (
    "water_temp_f",
    "setpoint_f",
    "heat_state",
    "heat_mode",
    "temperature_range",
    "pump1_state",
    "pump2_state",
    "pump3_state",
    "pump4_state",
    "circulation_pump_state",
    "blower1_state",
    "blower2_state",
    "light1_state",
    "light2_state",
    "mister_state",
    "aux1_state",
    "aux2_state",
)
