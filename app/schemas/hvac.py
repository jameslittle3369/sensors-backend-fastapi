from pydantic import BaseModel


class HvacZoneLogRequest(BaseModel):
    name: str

    # uiData
    disp_temperature: int | None = None
    heat_setpoint: int | None = None
    cool_setpoint: int | None = None
    display_units: str | None = None
    status_heat: str | None = None
    status_cool: str | None = None
    hold_until_capable: bool | None = None
    schedule_capable: bool | None = None
    dual_setpoint_status: bool | None = None
    schedule_heat_sp: int | None = None
    schedule_cool_sp: int | None = None
    system_switch_position: str | None = None
    indoor_humidity: int | None = None
    outdoor_temperature: int | None = None
    equipment_output_status: str | None = None

    # fanData
    fan_mode: str | None = None
    fan_is_running: bool | None = None


class HvacZoneLogResponse(BaseModel):
    external_id: str
    created: bool  # False when skipped due to dedup (nothing changed)
