from decimal import Decimal

from pydantic import BaseModel


class AnemometerLogRequest(BaseModel):
    name: str
    speed_mph: Decimal
    direction_deg: Decimal


class AnemometerLogResponse(BaseModel):
    external_id: str
    created: bool  # False when skipped due to dedup (unchanged reading)
