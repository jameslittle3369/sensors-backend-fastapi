from datetime import UTC, datetime

from sqlalchemy import Column
from sqlalchemy import DateTime as SADateTime
from sqlmodel import Field, SQLModel


class HvacZone(SQLModel, table=True):
    __tablename__ = "hvac_zones"

    external_id: str = Field(max_length=50, primary_key=True)  # pyhtcc DeviceID, as str
    name: str = Field(max_length=200)


class HvacZoneLog(SQLModel, table=True):
    """Each field mirrors a raw key from pyhtcc's uiData/fanData blocks
    verbatim (snake_cased). Originally logged all 53 raw fields for
    open-ended Grafana time-series charting; pruned to these 17 after
    studying real data showed the rest never or rarely changed."""

    __tablename__ = "hvac_zone_logs"

    id: int | None = Field(default=None, primary_key=True)
    hvac_zone_id: str = Field(foreign_key="hvac_zones.external_id", max_length=50, index=True)
    recorded_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(SADateTime(timezone=True), nullable=False),
    )

    # uiData -- pruned to 15 fields (from the original 47) after studying
    # real logged data: everything removed here never or rarely changed
    # (capability/allowed/available/not_fault flags, hold/vacation
    # bookkeeping, status/limit fields).
    disp_temperature: int | None = Field(default=None)
    heat_setpoint: int | None = Field(default=None)
    cool_setpoint: int | None = Field(default=None)
    display_units: str | None = Field(default=None, max_length=8)
    status_heat: int | None = Field(default=None)
    status_cool: int | None = Field(default=None)
    hold_until_capable: bool | None = Field(default=None)
    schedule_capable: bool | None = Field(default=None)
    dual_setpoint_status: bool | None = Field(default=None)
    schedule_heat_sp: int | None = Field(default=None)
    schedule_cool_sp: int | None = Field(default=None)
    # Stored as pyhtcc's SystemMode enum name (e.g. "Cool"), not the raw
    # int -- readable directly in Grafana/psql with no CASE/join needed.
    system_switch_position: str | None = Field(default=None, max_length=20)
    indoor_humidity: int | None = Field(default=None)
    outdoor_temperature: int | None = Field(default=None)
    equipment_output_status: int | None = Field(default=None)

    # fanData
    # Stored as pyhtcc's FanMode enum name (e.g. "Auto"), not the raw int
    # -- same rationale as system_switch_position above.
    fan_mode: str | None = Field(default=None, max_length=20)
    fan_is_running: bool | None = Field(default=None)


# Field names shared between HvacZoneLogRequest and HvacZoneLog that
# participate in dedup comparison (everything except identity/bookkeeping
# columns) -- kept here so the router and any future tooling share one
# source of truth for "what counts as a metric."
HVAC_ZONE_LOG_METRIC_FIELDS: tuple[str, ...] = (
    "disp_temperature",
    "heat_setpoint",
    "cool_setpoint",
    "display_units",
    "status_heat",
    "status_cool",
    "hold_until_capable",
    "schedule_capable",
    "dual_setpoint_status",
    "schedule_heat_sp",
    "schedule_cool_sp",
    "system_switch_position",
    "indoor_humidity",
    "outdoor_temperature",
    "equipment_output_status",
    "fan_mode",
    "fan_is_running",
)
