from datetime import datetime

from pydantic import BaseModel


class IkeaDeviceLogRequest(BaseModel):
    name: str
    battery_pct: int
    last_seen_at: datetime | None = None


class IkeaDeviceLogResponse(BaseModel):
    external_id: str
    name: str
    battery_pct: int | None
    last_seen_at: datetime | None
