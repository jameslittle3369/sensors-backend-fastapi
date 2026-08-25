from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import Column
from sqlalchemy import DateTime as SADateTime
from sqlmodel import Field, SQLModel


class RainGauge(SQLModel, table=True):
    __tablename__ = "raingauges"

    external_id: str = Field(max_length=50, primary_key=True)  # rtl_433 sensor id, as str
    name: str = Field(max_length=200)
    # rtl_433's rain_in is a raw accumulating hardware counter (resets
    # every 5.11in), not a true rolling 24h figure -- this is just the
    # latest raw counter reading, named without "24h" to avoid implying
    # otherwise. A real rolling-window figure is a later follow-up.
    current_rain_in: Decimal | None = Field(default=None, max_digits=6, decimal_places=2)


class RainGaugeLog(SQLModel, table=True):
    __tablename__ = "raingauge_logs"

    id: int | None = Field(default=None, primary_key=True)
    raingauge_id: str = Field(foreign_key="raingauges.external_id", max_length=50, index=True)
    rain_in: Decimal = Field(max_digits=6, decimal_places=2)
    recorded_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(SADateTime(timezone=True), nullable=False),
    )
