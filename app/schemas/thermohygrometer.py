from pydantic import BaseModel


class ThermoHygrometerListItem(BaseModel):
    id_channel: str
    pretty_name: str
    # ThermoHygrometerListSerializer.get_last is hardcoded to `return
    # None` unconditionally in Django (dead code below it is
    # unreachable) -- ported verbatim, always null.
    last: None = None
