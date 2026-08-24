from pydantic import BaseModel


class HvacZoneLogRequest(BaseModel):
    name: str

    # uiData
    disp_temperature: int | None = None
    heat_setpoint: int | None = None
    cool_setpoint: int | None = None
    display_units: str | None = None
    status_heat: int | None = None
    status_cool: int | None = None
    hold_until_capable: bool | None = None
    schedule_capable: bool | None = None
    vacation_hold: int | None = None
    dual_setpoint_status: bool | None = None
    heat_next_period: int | None = None
    cool_next_period: int | None = None
    heat_lower_setpt_limit: int | None = None
    heat_upper_setpt_limit: int | None = None
    cool_lower_setpt_limit: int | None = None
    cool_upper_setpt_limit: int | None = None
    schedule_heat_sp: int | None = None
    schedule_cool_sp: int | None = None
    switch_auto_allowed: bool | None = None
    switch_cool_allowed: bool | None = None
    switch_off_allowed: bool | None = None
    switch_heat_allowed: bool | None = None
    switch_emergency_heat_allowed: bool | None = None
    system_switch_position: str | None = None
    deadband: int | None = None
    indoor_humidity: int | None = None
    commercial: bool | None = None
    disp_temperature_available: bool | None = None
    indoor_humidity_sensor_available: bool | None = None
    indoor_humidity_sensor_not_fault: bool | None = None
    vacation_hold_until_time: int | None = None
    temporary_hold_until_time: int | None = None
    is_in_vacation_hold_mode: bool | None = None
    vacation_hold_cancelable: bool | None = None
    setpoint_change_allowed: bool | None = None
    outdoor_temperature: int | None = None
    outdoor_humidity: int | None = None
    outdoor_humidity_available: bool | None = None
    outdoor_temperature_available: bool | None = None
    disp_temperature_status: int | None = None
    indoor_humid_status: int | None = None
    outdoor_temp_status: int | None = None
    outdoor_humid_status: int | None = None
    outdoor_temperature_sensor_not_fault: bool | None = None
    outdoor_humidity_sensor_not_fault: bool | None = None
    current_setpoint_status: int | None = None
    equipment_output_status: int | None = None

    # fanData
    fan_mode: str | None = None
    fan_mode_auto_allowed: bool | None = None
    fan_mode_on_allowed: bool | None = None
    fan_mode_circulate_allowed: bool | None = None
    fan_mode_follow_schedule_allowed: bool | None = None
    fan_is_running: bool | None = None


class HvacZoneLogResponse(BaseModel):
    external_id: str
    created: bool  # False when skipped due to dedup (nothing changed)
