"""log hvac status_heat, status_cool, equipment_output_status as enum names

Revision ID: 51de07cbc136
Revises: e15d91686ce4
Create Date: 2026-08-24 21:18:41.751720

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '51de07cbc136'
down_revision: Union[str, Sequence[str], None] = 'e15d91686ce4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Not pyhtcc-native enums (unlike system_switch_position/fan_mode) --
# reverse-engineered from `somecomfort`, cross-validated against
# pyhtcc's own control-write methods. See sensors-apps/honeywell's
# HoldStatus/EquipmentStatus for the source of truth. An unrecognized
# existing int maps to NULL rather than a fabricated label.
_HOLD_STATUS_TO_NAME = """
    CASE {col}
        WHEN 0 THEN 'Schedule'
        WHEN 1 THEN 'Temporary'
        WHEN 2 THEN 'Permanent'
        ELSE NULL
    END
"""
_NAME_TO_HOLD_STATUS = """
    CASE {col}
        WHEN 'Schedule' THEN 0
        WHEN 'Temporary' THEN 1
        WHEN 'Permanent' THEN 2
        ELSE NULL
    END
"""
_EQUIPMENT_STATUS_TO_NAME = """
    CASE equipment_output_status
        WHEN 0 THEN 'OffOrFan'
        WHEN 1 THEN 'Heat'
        WHEN 2 THEN 'Cool'
        ELSE NULL
    END
"""
_NAME_TO_EQUIPMENT_STATUS = """
    CASE equipment_output_status
        WHEN 'OffOrFan' THEN 0
        WHEN 'Heat' THEN 1
        WHEN 'Cool' THEN 2
        ELSE NULL
    END
"""


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        'hvac_zone_logs', 'status_heat',
        existing_type=sa.INTEGER(),
        type_=sqlmodel.sql.sqltypes.AutoString(length=20),
        existing_nullable=True,
        postgresql_using=_HOLD_STATUS_TO_NAME.format(col='status_heat'),
    )
    op.alter_column(
        'hvac_zone_logs', 'status_cool',
        existing_type=sa.INTEGER(),
        type_=sqlmodel.sql.sqltypes.AutoString(length=20),
        existing_nullable=True,
        postgresql_using=_HOLD_STATUS_TO_NAME.format(col='status_cool'),
    )
    op.alter_column(
        'hvac_zone_logs', 'equipment_output_status',
        existing_type=sa.INTEGER(),
        type_=sqlmodel.sql.sqltypes.AutoString(length=20),
        existing_nullable=True,
        postgresql_using=_EQUIPMENT_STATUS_TO_NAME,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'hvac_zone_logs', 'equipment_output_status',
        existing_type=sqlmodel.sql.sqltypes.AutoString(length=20),
        type_=sa.INTEGER(),
        existing_nullable=True,
        postgresql_using=_NAME_TO_EQUIPMENT_STATUS,
    )
    op.alter_column(
        'hvac_zone_logs', 'status_cool',
        existing_type=sqlmodel.sql.sqltypes.AutoString(length=20),
        type_=sa.INTEGER(),
        existing_nullable=True,
        postgresql_using=_NAME_TO_HOLD_STATUS.format(col='status_cool'),
    )
    op.alter_column(
        'hvac_zone_logs', 'status_heat',
        existing_type=sqlmodel.sql.sqltypes.AutoString(length=20),
        type_=sa.INTEGER(),
        existing_nullable=True,
        postgresql_using=_NAME_TO_HOLD_STATUS.format(col='status_heat'),
    )
