from decimal import Decimal

from pydantic import BaseModel


class ThermoHygrometerListItem(BaseModel):
    id_channel: str
    pretty_name: str
    # ThermoHygrometerListSerializer.get_last is hardcoded to `return
    # None` unconditionally in Django (dead code below it is
    # unreachable) -- ported verbatim, always null.
    last: None = None


class ThermoHygrometerLogRequest(BaseModel):
    pretty_name: str | None = None
    temp_f: Decimal
    humidity: Decimal
    battery_ok: bool | None = None


class ThermoHygrometerLogResponse(BaseModel):
    id_channel: str
    created: bool  # False when skipped due to dedup (unchanged reading)
