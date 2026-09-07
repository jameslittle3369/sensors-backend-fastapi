from decimal import Decimal

from pydantic import BaseModel


class SpaLogRequest(BaseModel):
    name: str

    water_temp_f: Decimal | None = None
    setpoint_f: Decimal | None = None
    heat_state: str | None = None
    heat_mode: str | None = None
    temperature_range: str | None = None

    pump1_state: str | None = None
    pump2_state: str | None = None
    pump3_state: str | None = None
    pump4_state: str | None = None
    circulation_pump_state: str | None = None
    blower1_state: str | None = None
    blower2_state: str | None = None
    light1_state: str | None = None
    light2_state: str | None = None
    mister_state: str | None = None
    aux1_state: str | None = None
    aux2_state: str | None = None


class SpaLogResponse(BaseModel):
    external_id: str
    created: bool  # False when skipped due to dedup (nothing changed)
