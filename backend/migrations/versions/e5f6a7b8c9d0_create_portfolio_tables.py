"""create_portfolio_tables

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-03-13 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- positions ---
    op.create_table(
        'positions',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('strategy_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('strategies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('symbol', sa.String(50), nullable=False),
        sa.Column('market', sa.String(20), nullable=False),
        sa.Column('side', sa.String(10), nullable=False),
        sa.Column('qty', sa.Numeric(18, 8), nullable=False),
        sa.Column('avg_entry_price', sa.Numeric(18, 8), nullable=False),
        sa.Column('cost_basis', sa.Numeric(18, 2), nullable=False),
        sa.Column('current_price', sa.Numeric(18, 8), nullable=False),
        sa.Column('market_value', sa.Numeric(18, 2), nullable=False),
        sa.Column('unrealized_pnl', sa.Numeric(18, 2), nullable=False, server_default='0'),
        sa.Column('unrealized_pnl_percent', sa.Numeric(10, 4), nullable=False, server_default='0'),
        sa.Column('realized_pnl', sa.Numeric(18, 2), nullable=False, server_default='0'),
        sa.Column('total_fees', sa.Numeric(18, 2), nullable=False, server_default='0'),
        sa.Column('total_dividends_received', sa.Numeric(18, 2), nullable=False, server_default='0'),
        sa.Column('total_return', sa.Numeric(18, 2), nullable=False, server_default='0'),
        sa.Column('total_return_percent', sa.Numeric(10, 4), nullable=False, server_default='0'),
        sa.Column('status', sa.String(20), nullable=False, server_default='open'),
        sa.Column('opened_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('close_reason', sa.String(30), nullable=True),
        sa.Column('highest_price_since_entry', sa.Numeric(18, 8), nullable=False),
        sa.Column('lowest_price_since_entry', sa.Numeric(18, 8), nullable=False),
        sa.Column('bars_held', sa.Integer, nullable=False, server_default='0'),
        sa.Column('broker_account_id', sa.String(100), nullable=True),
        sa.Column('underlying_symbol', sa.String(50), nullable=True),
        sa.Column('contract_type', sa.String(10), nullable=True),
        sa.Column('strike_price', sa.Numeric(18, 8), nullable=True),
        sa.Column('expiration_date', sa.Date, nullable=True),
        sa.Column('contract_multiplier', sa.Integer, nullable=False, server_default='1'),
        sa.Column('user_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
    )

    op.create_index('ix_positions_strategy_status', 'positions', ['strategy_id', 'status'])
    op.create_index('ix_positions_symbol_status', 'positions', ['symbol', 'status'])
    op.create_index('ix_positions_status', 'positions', ['status'])
    op.create_index('ix_positions_strategy_symbol_status', 'positions',
                    ['strategy_id', 'symbol', 'status'])
    op.create_index('ix_positions_user_status', 'positions', ['user_id', 'status'])
    op.create_index('ix_positions_broker_account_status', 'positions',
                    ['broker_account_id', 'status'],
                    postgresql_where=sa.text('broker_account_id IS NOT NULL'))
    op.create_index('ix_positions_expiration_date', 'positions',
                    ['expiration_date'],
                    postgresql_where=sa.text('expiration_date IS NOT NULL'))

    # --- cash_balances ---
    op.create_table(
        'cash_balances',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('account_scope', sa.String(50), nullable=False),
        sa.Column('balance', sa.Numeric(18, 2), nullable=False),
        sa.Column('user_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.UniqueConstraint('account_scope', 'user_id', name='uq_cash_balance_scope_user'),
    )

    # --- portfolio_meta ---
    op.create_table(
        'portfolio_meta',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('key', sa.String(100), nullable=False),
        sa.Column('value', sa.String(500), nullable=False),
        sa.Column('user_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.UniqueConstraint('key', 'user_id', name='uq_portfolio_meta_key_user'),
    )


def downgrade() -> None:
    op.drop_table('portfolio_meta')
    op.drop_table('cash_balances')
    op.drop_index('ix_positions_expiration_date', table_name='positions')
    op.drop_index('ix_positions_broker_account_status', table_name='positions')
    op.drop_index('ix_positions_user_status', table_name='positions')
    op.drop_index('ix_positions_strategy_symbol_status', table_name='positions')
    op.drop_index('ix_positions_status', table_name='positions')
    op.drop_index('ix_positions_symbol_status', table_name='positions')
    op.drop_index('ix_positions_strategy_status', table_name='positions')
    op.drop_table('positions')
