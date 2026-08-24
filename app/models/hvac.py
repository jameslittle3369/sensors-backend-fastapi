from datetime import UTC, datetime

from sqlalchemy import Column
from sqlalchemy import DateTime as SADateTime
from sqlmodel import Field, SQLModel


class HvacZone(SQLModel, table=True):
    __tablename__ = "hvac_zones"

    external_id: str = Field(max_length=50, primary_key=True)  # pyhtcc DeviceID, as str
    name: str = Field(max_length=200)


class HvacZoneLog(SQLModel, table=True):
    """Every field mirrors a raw key from pyhtcc's uiData/fanData blocks
    verbatim (snake_cased), rather than a curated subset -- logged wide for
    open-ended Grafana time-series charting, to be pruned later once it's
    clear which fields are actually useful."""

    __tablename__ = "hvac_zone_logs"

    id: int | None = Field(default=None, primary_key=True)
    hvac_zone_id: str = Field(foreign_key="hvac_zones.external_id", max_length=50, index=True)
    recorded_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(SADateTime(timezone=True), nullable=False),
    )

    # uiData
    disp_temperature: int | None = Field(default=None)
    heat_setpoint: int | None = Field(default=None)
    cool_setpoint: int | None = Field(default=None)
    display_units: str | None = Field(default=None, max_length=8)
    status_heat: int | None = Field(default=None)
    status_cool: int | None = Field(default=None)
    hold_until_capable: bool | None = Field(default=None)
    schedule_capable: bool | None = Field(default=None)
    vacation_hold: int | None = Field(default=None)
    dual_setpoint_status: bool | None = Field(default=None)
    heat_next_period: int | None = Field(default=None)
    cool_next_period: int | None = Field(default=None)
    heat_lower_setpt_limit: int | None = Field(default=None)
    heat_upper_setpt_limit: int | None = Field(default=None)
    cool_lower_setpt_limit: int | None = Field(default=None)
    cool_upper_setpt_limit: int | None = Field(default=None)
    schedule_heat_sp: int | None = Field(default=None)
    schedule_cool_sp: int | None = Field(default=None)
    switch_auto_allowed: bool | None = Field(default=None)
    switch_cool_allowed: bool | None = Field(default=None)
    switch_off_allowed: bool | None = Field(default=None)
    switch_heat_allowed: bool | None = Field(default=None)
    switch_emergency_heat_allowed: bool | None = Field(default=None)
    system_switch_position: int | None = Field(default=None)
    deadband: int | None = Field(default=None)
    indoor_humidity: int | None = Field(default=None)
    commercial: bool | None = Field(default=None)
    disp_temperature_available: bool | None = Field(default=None)
    indoor_humidity_sensor_available: bool | None = Field(default=None)
    indoor_humidity_sensor_not_fault: bool | None = Field(default=None)
    vacation_hold_until_time: int | None = Field(default=None)
    temporary_hold_until_time: int | None = Field(default=None)
    is_in_vacation_hold_mode: bool | None = Field(default=None)
    vacation_hold_cancelable: bool | None = Field(default=None)
    setpoint_change_allowed: bool | None = Field(default=None)
    outdoor_temperature: int | None = Field(default=None)
    outdoor_humidity: int | None = Field(default=None)
    outdoor_humidity_available: bool | None = Field(default=None)
    outdoor_temperature_available: bool | None = Field(default=None)
    disp_temperature_status: int | None = Field(default=None)
    indoor_humid_status: int | None = Field(default=None)
    outdoor_temp_status: int | None = Field(default=None)
    outdoor_humid_status: int | None = Field(default=None)
    outdoor_temperature_sensor_not_fault: bool | None = Field(default=None)
    outdoor_humidity_sensor_not_fault: bool | None = Field(default=None)
    current_setpoint_status: int | None = Field(default=None)
    equipment_output_status: int | None = Field(default=None)

    # fanData
    fan_mode: int | None = Field(default=None)
    fan_mode_auto_allowed: bool | None = Field(default=None)
    fan_mode_on_allowed: bool | None = Field(default=None)
    fan_mode_circulate_allowed: bool | None = Field(default=None)
    fan_mode_follow_schedule_allowed: bool | None = Field(default=None)
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
    "vacation_hold",
    "dual_setpoint_status",
    "heat_next_period",
    "cool_next_period",
    "heat_lower_setpt_limit",
    "heat_upper_setpt_limit",
    "cool_lower_setpt_limit",
    "cool_upper_setpt_limit",
    "schedule_heat_sp",
    "schedule_cool_sp",
    "switch_auto_allowed",
    "switch_cool_allowed",
    "switch_off_allowed",
    "switch_heat_allowed",
    "switch_emergency_heat_allowed",
    "system_switch_position",
    "deadband",
    "indoor_humidity",
    "commercial",
    "disp_temperature_available",
    "indoor_humidity_sensor_available",
    "indoor_humidity_sensor_not_fault",
    "vacation_hold_until_time",
    "temporary_hold_until_time",
    "is_in_vacation_hold_mode",
    "vacation_hold_cancelable",
    "setpoint_change_allowed",
    "outdoor_temperature",
    "outdoor_humidity",
    "outdoor_humidity_available",
    "outdoor_temperature_available",
    "disp_temperature_status",
    "indoor_humid_status",
    "outdoor_temp_status",
    "outdoor_humid_status",
    "outdoor_temperature_sensor_not_fault",
    "outdoor_humidity_sensor_not_fault",
    "current_setpoint_status",
    "equipment_output_status",
    "fan_mode",
    "fan_mode_auto_allowed",
    "fan_mode_on_allowed",
    "fan_mode_circulate_allowed",
    "fan_mode_follow_schedule_allowed",
    "fan_is_running",
)
