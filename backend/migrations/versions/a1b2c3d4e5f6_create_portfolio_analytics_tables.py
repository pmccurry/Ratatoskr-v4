"""create_portfolio_analytics_tables

Revision ID: g7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-03-13 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'g7b8c9d0e1f2'
down_revision: Union[str, None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- portfolio_snapshots ---
    op.create_table(
        'portfolio_snapshots',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('ts', sa.DateTime(timezone=True), nullable=False),
        sa.Column('cash_balance', sa.Numeric(18, 2), nullable=False),
        sa.Column('positions_value', sa.Numeric(18, 2), nullable=False),
        sa.Column('equity', sa.Numeric(18, 2), nullable=False),
        sa.Column('unrealized_pnl', sa.Numeric(18, 2), nullable=False),
        sa.Column('realized_pnl_today', sa.Numeric(18, 2), nullable=False),
        sa.Column('realized_pnl_total', sa.Numeric(18, 2), nullable=False),
        sa.Column('dividend_income_today', sa.Numeric(18, 2), nullable=False),
        sa.Column('dividend_income_total', sa.Numeric(18, 2), nullable=False),
        sa.Column('drawdown_percent', sa.Numeric(10, 4), nullable=False),
        sa.Column('peak_equity', sa.Numeric(18, 2), nullable=False),
        sa.Column('open_positions_count', sa.Integer, nullable=False),
        sa.Column('snapshot_type', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
    )
    op.create_index('ix_portfolio_snapshots_ts', 'portfolio_snapshots', ['ts'])
    op.create_index('ix_portfolio_snapshots_type_ts', 'portfolio_snapshots',
                    ['snapshot_type', 'ts'])
    op.create_index('ix_portfolio_snapshots_user_ts', 'portfolio_snapshots',
                    ['user_id', 'ts'])

    # --- realized_pnl_entries ---
    op.create_table(
        'realized_pnl_entries',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('position_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('positions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('strategy_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('strategies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('symbol', sa.String(50), nullable=False),
        sa.Column('market', sa.String(20), nullable=False),
        sa.Column('side', sa.String(10), nullable=False),
        sa.Column('qty_closed', sa.Numeric(18, 8), nullable=False),
        sa.Column('entry_price', sa.Numeric(18, 8), nullable=False),
        sa.Column('exit_price', sa.Numeric(18, 8), nullable=False),
        sa.Column('gross_pnl', sa.Numeric(18, 2), nullable=False),
        sa.Column('fees', sa.Numeric(18, 2), nullable=False),
        sa.Column('net_pnl', sa.Numeric(18, 2), nullable=False),
        sa.Column('pnl_percent', sa.Numeric(10, 4), nullable=False),
        sa.Column('holding_period_bars', sa.Integer, nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
    )
    op.create_index('ix_realized_pnl_entries_strategy_closed', 'realized_pnl_entries',
                    ['strategy_id', 'closed_at'])
    op.create_index('ix_realized_pnl_entries_symbol_closed', 'realized_pnl_entries',
                    ['symbol', 'closed_at'])
    op.create_index('ix_realized_pnl_entries_closed_at', 'realized_pnl_entries',
                    ['closed_at'])
    op.create_index('ix_realized_pnl_entries_user_closed', 'realized_pnl_entries',
                    ['user_id', 'closed_at'])

    # --- dividend_payments ---
    op.create_table(
        'dividend_payments',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('position_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('positions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('announcement_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('dividend_announcements.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('symbol', sa.String(50), nullable=False),
        sa.Column('ex_date', sa.Date, nullable=False),
        sa.Column('payable_date', sa.Date, nullable=False),
        sa.Column('shares_held', sa.Numeric(18, 8), nullable=False),
        sa.Column('amount_per_share', sa.Numeric(18, 8), nullable=False),
        sa.Column('gross_amount', sa.Numeric(18, 2), nullable=False),
        sa.Column('net_amount', sa.Numeric(18, 2), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
    )
    op.create_index('ix_dividend_payments_position', 'dividend_payments',
                    ['position_id'])
    op.create_index('ix_dividend_payments_user_payable', 'dividend_payments',
                    ['user_id', 'payable_date'])
    op.create_index('ix_dividend_payments_status', 'dividend_payments',
                    ['status'])

    # --- split_adjustments ---
    op.create_table(
        'split_adjustments',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('symbol', sa.String(50), nullable=False),
        sa.Column('split_type', sa.String(20), nullable=False),
        sa.Column('old_rate', sa.Integer, nullable=False),
        sa.Column('new_rate', sa.Integer, nullable=False),
        sa.Column('effective_date', sa.Date, nullable=False),
        sa.Column('positions_adjusted', sa.Integer, nullable=False),
        sa.Column('adjustments_json', sa.dialects.postgresql.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
    )
    op.create_index('ix_split_adjustments_symbol_date', 'split_adjustments',
                    ['symbol', 'effective_date'])


def downgrade() -> None:
    op.drop_index('ix_split_adjustments_symbol_date', table_name='split_adjustments')
    op.drop_table('split_adjustments')

    op.drop_index('ix_dividend_payments_status', table_name='dividend_payments')
    op.drop_index('ix_dividend_payments_user_payable', table_name='dividend_payments')
    op.drop_index('ix_dividend_payments_position', table_name='dividend_payments')
    op.drop_table('dividend_payments')

    op.drop_index('ix_realized_pnl_entries_user_closed', table_name='realized_pnl_entries')
    op.drop_index('ix_realized_pnl_entries_closed_at', table_name='realized_pnl_entries')
    op.drop_index('ix_realized_pnl_entries_symbol_closed', table_name='realized_pnl_entries')
    op.drop_index('ix_realized_pnl_entries_strategy_closed', table_name='realized_pnl_entries')
    op.drop_table('realized_pnl_entries')

    op.drop_index('ix_portfolio_snapshots_user_ts', table_name='portfolio_snapshots')
    op.drop_index('ix_portfolio_snapshots_type_ts', table_name='portfolio_snapshots')
    op.drop_index('ix_portfolio_snapshots_ts', table_name='portfolio_snapshots')
    op.drop_table('portfolio_snapshots')
