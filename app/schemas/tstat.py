from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class TstatLogRepr(BaseModel):
    at: datetime
    f: Decimal


class ThermometerListItem(BaseModel):
    # No id/romid exposed here -- Django's ThermometerListSerializer.Meta
    # fields are literally just ['url', 'pretty_name', 'last'].
    url: str
    pretty_name: str
    last: Decimal | None


class ThermometerRetrieveOut(BaseModel):
    romid: str
    pretty_name: str
    last: TstatLogRepr | None
    high_last24: TstatLogRepr | None
    low_last24: TstatLogRepr | None
