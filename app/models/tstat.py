from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import Column, Index
from sqlalchemy import DateTime as SADateTime
from sqlmodel import Field, SQLModel


class Thermometer(SQLModel, table=True):
    __tablename__ = "tstats_thermometer"
    # Django adds a varchar_pattern_ops index alongside the PK's own
    # btree index, for pattern-matching (LIKE 'foo%') queries on the
    # varchar PK. SQLAlchemy doesn't create this automatically -- named
    # to match Django's exact index name so Alembic sees no diff.
    __table_args__ = (
        Index(
            "tstats_thermometer_romid_4ef89f28_like",
            "romid",
            postgresql_ops={"romid": "varchar_pattern_ops"},
        ),
    )

    # Natural string primary key (a 1-Wire ROM ID), not autoincrement.
    romid: str = Field(max_length=50, primary_key=True)
    pretty_name: str = Field(max_length=50)
    current: Decimal = Field(default=0, max_digits=8, decimal_places=4)
    high_24_hour: Decimal = Field(default=0, max_digits=8, decimal_places=4)
    low_24_hour: Decimal = Field(default=0, max_digits=8, decimal_places=4)


class TstatLog(SQLModel, table=True):
    __tablename__ = "tstats_tstatlog"
    # Matches Django's exact index names (a plain btree plus a
    # varchar_pattern_ops variant) rather than relying on Field(index=True),
    # which would generate a differently-named index and show up as a
    # permanent no-op diff in `alembic check`.
    __table_args__ = (
        Index("tstats_tstatlog_romid_id_e6e55d6a", "romid_id"),
        Index(
            "tstats_tstatlog_romid_id_e6e55d6a_like",
            "romid_id",
            postgresql_ops={"romid_id": "varchar_pattern_ops"},
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    # Django's FK field was literally named "romid" (a ForeignKey to
    # Thermometer), so the DB column is romid_id. NOT a real DB-level FK
    # constraint though -- verified via \d+ tstats_tstatlog, the live
    # schema only has a plain index here (tstats_tstatlog_romid_id_e6e55d6a),
    # no "Foreign-key constraints:" section. Likely dropped deliberately
    # for insert performance on this high-volume log table. Don't
    # declare foreign_key= here -- that would make Alembic think a
    # constraint needs to be added that was never actually there.
    romid_id: str = Field(max_length=50)
    primary_value: Decimal = Field(max_digits=8, decimal_places=4)
    # Live schema (verified via \d+ tstats_tstatlog) is `timestamp with
    # time zone`, NOT NULL -- Django's naive default=datetime.now was
    # converted to aware UTC on save because USE_TZ=True. Keep this
    # tz-aware. nullable=False must be explicit: passing a custom
    # sa_column= bypasses SQLModel's usual nullability inference from the
    # Python type.
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(SADateTime(timezone=True), nullable=False),
    )

    @property
    def degrees_farenheit(self) -> Decimal:
        return (self.primary_value * 9) / 5 + 32
