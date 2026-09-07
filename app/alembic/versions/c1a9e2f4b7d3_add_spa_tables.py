"""add spa tables

Revision ID: c1a9e2f4b7d3
Revises: b7c22bb9f561
Create Date: 2026-09-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'c1a9e2f4b7d3'
down_revision: Union[str, Sequence[str], None] = 'b7c22bb9f561'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('spas',
    sa.Column('external_id', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False),
    sa.PrimaryKeyConstraint('external_id')
    )
    op.create_table('spa_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('spa_id', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
    sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('water_temp_f', sa.Numeric(precision=5, scale=1), nullable=True),
    sa.Column('setpoint_f', sa.Numeric(precision=5, scale=1), nullable=True),
    sa.Column('heat_state', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True),
    sa.Column('heat_mode', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True),
    sa.Column('temperature_range', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True),
    sa.Column('pump1_state', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True),
    sa.Column('pump2_state', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True),
    sa.Column('pump3_state', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True),
    sa.Column('pump4_state', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True),
    sa.Column('circulation_pump_state', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True),
    sa.Column('blower1_state', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True),
    sa.Column('blower2_state', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True),
    sa.Column('light1_state', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True),
    sa.Column('light2_state', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True),
    sa.Column('mister_state', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True),
    sa.Column('aux1_state', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True),
    sa.Column('aux2_state', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True),
    sa.ForeignKeyConstraint(['spa_id'], ['spas.external_id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_spa_logs_recorded_at'), 'spa_logs', ['recorded_at'], unique=False)
    op.create_index(op.f('ix_spa_logs_spa_id'), 'spa_logs', ['spa_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_spa_logs_spa_id'), table_name='spa_logs')
    op.drop_index(op.f('ix_spa_logs_recorded_at'), table_name='spa_logs')
    op.drop_table('spa_logs')
    op.drop_table('spas')
