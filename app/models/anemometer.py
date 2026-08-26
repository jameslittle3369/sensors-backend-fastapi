from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import Column
from sqlalchemy import DateTime as SADateTime
from sqlmodel import Field, SQLModel


class Anemometer(SQLModel, table=True):
    __tablename__ = "anemometers"

    external_id: str = Field(max_length=50, primary_key=True)  # rtl_433 sensor id, as str
    name: str = Field(max_length=200)
    current_speed_mph: Decimal | None = Field(default=None, max_digits=6, decimal_places=1)
    current_direction_deg: Decimal | None = Field(default=None, max_digits=5, decimal_places=1)


class AnemometerLog(SQLModel, table=True):
    __tablename__ = "anemometer_logs"

    id: int | None = Field(default=None, primary_key=True)
    anemometer_id: str = Field(foreign_key="anemometers.external_id", max_length=50, index=True)
    speed_mph: Decimal = Field(max_digits=6, decimal_places=1)
    direction_deg: Decimal = Field(max_digits=5, decimal_places=1)
    recorded_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(SADateTime(timezone=True), nullable=False, index=True),
    )
