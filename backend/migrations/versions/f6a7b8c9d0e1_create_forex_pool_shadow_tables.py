"""create_forex_pool_shadow_tables

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-03-13 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- broker_accounts ---
    op.create_table(
        'broker_accounts',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('broker', sa.String(20), nullable=False, server_default='oanda'),
        sa.Column('account_id', sa.String(100), nullable=False, unique=True),
        sa.Column('account_type', sa.String(20), nullable=False, server_default='paper_virtual'),
        sa.Column('label', sa.String(200), nullable=False),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('capital_allocation', sa.Numeric(18, 2), nullable=False),
        sa.Column('credentials_env_key', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
    )
    op.create_index('ix_broker_accounts_broker_active', 'broker_accounts', ['broker', 'is_active'])

    # --- account_allocations ---
    op.create_table(
        'account_allocations',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('account_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('broker_accounts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('strategy_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('strategies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('symbol', sa.String(50), nullable=False),
        sa.Column('side', sa.String(10), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('allocated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('released_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
    )
    op.create_index('ix_account_allocations_account_symbol_status', 'account_allocations',
                    ['account_id', 'symbol', 'status'])
    op.create_index('ix_account_allocations_strategy_status', 'account_allocations',
                    ['strategy_id', 'status'])
    op.create_index('ix_account_allocations_symbol_status', 'account_allocations',
                    ['symbol', 'status'])

    # --- shadow_positions ---
    op.create_table(
        'shadow_positions',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('strategy_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('strategies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('symbol', sa.String(50), nullable=False),
        sa.Column('side', sa.String(10), nullable=False),
        sa.Column('qty', sa.Numeric(18, 8), nullable=False),
        sa.Column('avg_entry_price', sa.Numeric(18, 8), nullable=False),
        sa.Column('current_price', sa.Numeric(18, 8), nullable=False),
        sa.Column('unrealized_pnl', sa.Numeric(18, 2), nullable=False, server_default='0'),
        sa.Column('realized_pnl', sa.Numeric(18, 2), nullable=False, server_default='0'),
        sa.Column('status', sa.String(20), nullable=False, server_default='open'),
        sa.Column('stop_loss_price', sa.Numeric(18, 8), nullable=True),
        sa.Column('take_profit_price', sa.Numeric(18, 8), nullable=True),
        sa.Column('trailing_stop_price', sa.Numeric(18, 8), nullable=True),
        sa.Column('highest_price_since_entry', sa.Numeric(18, 8), nullable=True),
        sa.Column('opened_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('close_reason', sa.String(30), nullable=True),
        sa.Column('entry_signal_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('signals.id', ondelete='CASCADE'), nullable=False),
        sa.Column('exit_signal_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('signals.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
    )
    op.create_index('ix_shadow_positions_strategy_status', 'shadow_positions',
                    ['strategy_id', 'status'])
    op.create_index('ix_shadow_positions_symbol_status', 'shadow_positions',
                    ['symbol', 'status'])

    # --- shadow_fills ---
    op.create_table(
        'shadow_fills',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('signal_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('signals.id', ondelete='CASCADE'), nullable=False),
        sa.Column('strategy_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('strategies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('symbol', sa.String(50), nullable=False),
        sa.Column('side', sa.String(10), nullable=False),
        sa.Column('qty', sa.Numeric(18, 8), nullable=False),
        sa.Column('reference_price', sa.Numeric(18, 8), nullable=False),
        sa.Column('price', sa.Numeric(18, 8), nullable=False),
        sa.Column('fee', sa.Numeric(18, 2), nullable=False),
        sa.Column('slippage_bps', sa.Numeric(10, 4), nullable=False),
        sa.Column('gross_value', sa.Numeric(18, 2), nullable=False),
        sa.Column('net_value', sa.Numeric(18, 2), nullable=False),
        sa.Column('fill_type', sa.String(10), nullable=False),
        sa.Column('shadow_position_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('shadow_positions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('filled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
    )
    op.create_index('ix_shadow_fills_strategy_filled', 'shadow_fills',
                    ['strategy_id', 'filled_at'])
    op.create_index('ix_shadow_fills_position', 'shadow_fills',
                    ['shadow_position_id'])


def downgrade() -> None:
    op.drop_table('shadow_fills')
    op.drop_index('ix_shadow_positions_symbol_status', table_name='shadow_positions')
    op.drop_index('ix_shadow_positions_strategy_status', table_name='shadow_positions')
    op.drop_table('shadow_positions')
    op.drop_index('ix_account_allocations_symbol_status', table_name='account_allocations')
    op.drop_index('ix_account_allocations_strategy_status', table_name='account_allocations')
    op.drop_index('ix_account_allocations_account_symbol_status', table_name='account_allocations')
    op.drop_table('account_allocations')
    op.drop_index('ix_broker_accounts_broker_active', table_name='broker_accounts')
    op.drop_table('broker_accounts')
