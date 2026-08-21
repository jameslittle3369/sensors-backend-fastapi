from datetime import datetime

from pydantic import BaseModel


class RingDeviceLogRequest(BaseModel):
    name: str
    battery_life: int
    last_motion_at: datetime | None = None


class RingDeviceLogResponse(BaseModel):
    external_id: str
    name: str
    battery_life: int | None
    last_motion_at: datetime | None
