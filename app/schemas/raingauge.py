from decimal import Decimal

from pydantic import BaseModel


class RainGaugeLogRequest(BaseModel):
    name: str
    rain_in: Decimal


class RainGaugeLogResponse(BaseModel):
    external_id: str
    created: bool  # False when skipped due to dedup (unchanged reading)
