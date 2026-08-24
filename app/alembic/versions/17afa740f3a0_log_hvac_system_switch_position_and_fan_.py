"""log hvac system_switch_position and fan_mode as enum names

Revision ID: 17afa740f3a0
Revises: ecf1fdc29e9a
Create Date: 2026-08-24 14:37:26.354118

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '17afa740f3a0'
down_revision: Union[str, Sequence[str], None] = 'ecf1fdc29e9a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# pyhtcc's SystemMode/FanMode enums (see sensors-apps/honeywell), values
# fixed by the library -- an unrecognized existing int maps to NULL rather
# than a fabricated label.
_SYSTEM_MODE_TO_NAME = """
    CASE system_switch_position
        WHEN 0 THEN 'EMHeat'
        WHEN 1 THEN 'Heat'
        WHEN 2 THEN 'Off'
        WHEN 3 THEN 'Cool'
        WHEN 4 THEN 'AutoHeat'
        WHEN 5 THEN 'AutoCool'
        WHEN 6 THEN 'SouthernAway'
        WHEN 7 THEN 'Unknown'
        ELSE NULL
    END
"""
_NAME_TO_SYSTEM_MODE = """
    CASE system_switch_position
        WHEN 'EMHeat' THEN 0
        WHEN 'Heat' THEN 1
        WHEN 'Off' THEN 2
        WHEN 'Cool' THEN 3
        WHEN 'AutoHeat' THEN 4
        WHEN 'AutoCool' THEN 5
        WHEN 'SouthernAway' THEN 6
        WHEN 'Unknown' THEN 7
        ELSE NULL
    END
"""
_FAN_MODE_TO_NAME = """
    CASE fan_mode
        WHEN 0 THEN 'Auto'
        WHEN 1 THEN 'On'
        WHEN 2 THEN 'Circulate'
        WHEN 3 THEN 'FollowSchedule'
        WHEN 4 THEN 'Unknown'
        ELSE NULL
    END
"""
_NAME_TO_FAN_MODE = """
    CASE fan_mode
        WHEN 'Auto' THEN 0
        WHEN 'On' THEN 1
        WHEN 'Circulate' THEN 2
        WHEN 'FollowSchedule' THEN 3
        WHEN 'Unknown' THEN 4
        ELSE NULL
    END
"""


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        'hvac_zone_logs', 'system_switch_position',
        existing_type=sa.INTEGER(),
        type_=sqlmodel.sql.sqltypes.AutoString(length=20),
        existing_nullable=True,
        postgresql_using=_SYSTEM_MODE_TO_NAME,
    )
    op.alter_column(
        'hvac_zone_logs', 'fan_mode',
        existing_type=sa.INTEGER(),
        type_=sqlmodel.sql.sqltypes.AutoString(length=20),
        existing_nullable=True,
        postgresql_using=_FAN_MODE_TO_NAME,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'hvac_zone_logs', 'fan_mode',
        existing_type=sqlmodel.sql.sqltypes.AutoString(length=20),
        type_=sa.INTEGER(),
        existing_nullable=True,
        postgresql_using=_NAME_TO_FAN_MODE,
    )
    op.alter_column(
        'hvac_zone_logs', 'system_switch_position',
        existing_type=sqlmodel.sql.sqltypes.AutoString(length=20),
        type_=sa.INTEGER(),
        existing_nullable=True,
        postgresql_using=_NAME_TO_SYSTEM_MODE,
    )
