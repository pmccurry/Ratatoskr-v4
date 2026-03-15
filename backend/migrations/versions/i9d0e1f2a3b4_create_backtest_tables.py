"""create_backtest_tables

Revision ID: i9d0e1f2a3b4
Revises: h8c9d0e1f2a3
Create Date: 2026-03-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'i9d0e1f2a3b4'
down_revision: Union[str, None] = 'h8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- backtest_runs ---
    op.create_table(
        'backtest_runs',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('strategy_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('strategies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('strategy_config', sa.dialects.postgresql.JSONB, nullable=False),
        sa.Column('symbols', sa.dialects.postgresql.JSONB, nullable=False),
        sa.Column('timeframe', sa.String(10), nullable=False),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('initial_capital', sa.Numeric(20, 2), nullable=False,
                  server_default=sa.text('100000')),
        sa.Column('position_sizing', sa.dialects.postgresql.JSONB, nullable=False),
        sa.Column('exit_config', sa.dialects.postgresql.JSONB, nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Float, nullable=True),
        sa.Column('metrics', sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column('bars_processed', sa.Integer, nullable=True),
        sa.Column('total_trades', sa.Integer, nullable=True),
        sa.Column('error', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
    )
    op.create_index('ix_backtest_runs_strategy_id', 'backtest_runs', ['strategy_id'])
    op.create_index('ix_backtest_runs_status', 'backtest_runs', ['status'])

    # --- backtest_trades ---
    op.create_table(
        'backtest_trades',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('backtest_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('backtest_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('side', sa.String(10), nullable=False),
        sa.Column('quantity', sa.Numeric(20, 6), nullable=False),
        sa.Column('entry_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('entry_price', sa.Numeric(20, 8), nullable=False),
        sa.Column('entry_bar_index', sa.Integer, nullable=False),
        sa.Column('exit_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('exit_price', sa.Numeric(20, 8), nullable=True),
        sa.Column('exit_bar_index', sa.Integer, nullable=True),
        sa.Column('exit_reason', sa.String(20), nullable=True),
        sa.Column('pnl', sa.Numeric(20, 8), nullable=True),
        sa.Column('pnl_percent', sa.Numeric(10, 4), nullable=True),
        sa.Column('fees', sa.Numeric(20, 8), nullable=True),
        sa.Column('hold_bars', sa.Integer, nullable=True),
        sa.Column('max_favorable', sa.Numeric(20, 8), nullable=True),
        sa.Column('max_adverse', sa.Numeric(20, 8), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
    )
    op.create_index('ix_backtest_trades_backtest_id', 'backtest_trades', ['backtest_id'])

    # --- backtest_equity_curve ---
    op.create_table(
        'backtest_equity_curve',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('backtest_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('backtest_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('bar_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('bar_index', sa.Integer, nullable=False),
        sa.Column('equity', sa.Numeric(20, 2), nullable=False),
        sa.Column('cash', sa.Numeric(20, 2), nullable=False),
        sa.Column('open_positions', sa.Integer, nullable=False, server_default=sa.text('0')),
        sa.Column('unrealized_pnl', sa.Numeric(20, 8), nullable=False,
                  server_default=sa.text('0')),
        sa.Column('drawdown_pct', sa.Numeric(10, 4), nullable=False,
                  server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
    )
    op.create_index('ix_backtest_equity_curve_backtest_id', 'backtest_equity_curve',
                    ['backtest_id'])
    op.create_index('ix_backtest_equity_curve_backtest_bar', 'backtest_equity_curve',
                    ['backtest_id', 'bar_index'])


def downgrade() -> None:
    op.drop_table('backtest_equity_curve')
    op.drop_table('backtest_trades')
    op.drop_table('backtest_runs')
