"""create_signals_table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-13 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'signals',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('strategy_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('strategy_version', sa.String(20), nullable=False),
        sa.Column('symbol', sa.String(50), nullable=False),
        sa.Column('market', sa.String(20), nullable=False),
        sa.Column('timeframe', sa.String(10), nullable=False),
        sa.Column('side', sa.String(10), nullable=False),
        sa.Column('signal_type', sa.String(20), nullable=False),
        sa.Column('source', sa.String(20), nullable=False),
        sa.Column('confidence', sa.Numeric(3, 2), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('payload_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('position_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('exit_reason', sa.String(30), nullable=True),
        sa.Column('ts', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_signals_strategy_created', 'signals', ['strategy_id', 'created_at'])
    op.create_index('ix_signals_symbol_created', 'signals', ['symbol', 'created_at'])
    op.create_index('ix_signals_status', 'signals', ['status'])
    op.create_index('ix_signals_strategy_symbol_status', 'signals', ['strategy_id', 'symbol', 'status'])


def downgrade() -> None:
    op.drop_index('ix_signals_strategy_symbol_status', table_name='signals')
    op.drop_index('ix_signals_status', table_name='signals')
    op.drop_index('ix_signals_symbol_created', table_name='signals')
    op.drop_index('ix_signals_strategy_created', table_name='signals')
    op.drop_table('signals')
