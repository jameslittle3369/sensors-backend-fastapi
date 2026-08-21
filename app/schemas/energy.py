from decimal import Decimal

from pydantic import BaseModel


class EnergyCircuitLogRequest(BaseModel):
    name: str
    watts: Decimal
    kwh_today: Decimal | None = None
    kwh_7d: Decimal | None = None
    kwh_30d: Decimal | None = None
    kwh_mtd: Decimal | None = None


class EnergyCircuitLogResponse(BaseModel):
    source: str
    external_id: str
    name: str
    current_watts: Decimal | None
    kwh_today: Decimal | None
    kwh_7d: Decimal | None
    kwh_30d: Decimal | None
    kwh_mtd: Decimal | None
