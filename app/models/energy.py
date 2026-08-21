from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import Column, UniqueConstraint
from sqlalchemy import DateTime as SADateTime
from sqlmodel import Field, SQLModel


class EnergyCircuit(SQLModel, table=True):
    __tablename__ = "energy_circuits"
    # (source, external_id) identifies a circuit -- the same external_id
    # could coincidentally collide between two different sources (emporia
    # vs kasa), so the uniqueness scope is the pair, not external_id alone.
    __table_args__ = (UniqueConstraint("source", "external_id"),)

    id: int | None = Field(default=None, primary_key=True)
    source: str = Field(max_length=20)
    external_id: str = Field(max_length=100)
    name: str = Field(max_length=200)
    # Latest-known snapshot, updated on every log write. Nullable since not
    # every source necessarily reports every rollup window.
    current_watts: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)
    kwh_today: Decimal | None = Field(default=None, max_digits=10, decimal_places=3)
    kwh_7d: Decimal | None = Field(default=None, max_digits=10, decimal_places=3)
    kwh_30d: Decimal | None = Field(default=None, max_digits=10, decimal_places=3)
    kwh_mtd: Decimal | None = Field(default=None, max_digits=10, decimal_places=3)


class EnergyCircuitLog(SQLModel, table=True):
    __tablename__ = "energy_circuit_logs"

    id: int | None = Field(default=None, primary_key=True)
    circuit_id: int = Field(foreign_key="energy_circuits.id", index=True)
    # Circuits only log current usage -- the kWh rollups live on the
    # parent EnergyCircuit row as the latest-known snapshot, not repeated
    # in every log row.
    watts: Decimal = Field(max_digits=10, decimal_places=2)
    recorded_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(SADateTime(timezone=True), nullable=False),
    )
