"""create_paper_trading_tables

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-03-13 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # paper_orders
    op.create_table(
        'paper_orders',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('signal_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('risk_decision_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('strategy_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('symbol', sa.String(50), nullable=False),
        sa.Column('market', sa.String(20), nullable=False),
        sa.Column('side', sa.String(10), nullable=False),
        sa.Column('order_type', sa.String(20), nullable=False),
        sa.Column('signal_type', sa.String(20), nullable=False),
        sa.Column('requested_qty', sa.Numeric(18, 8), nullable=False),
        sa.Column('requested_price', sa.Numeric(18, 8), nullable=True),
        sa.Column('filled_qty', sa.Numeric(18, 8), nullable=False, server_default='0'),
        sa.Column('filled_avg_price', sa.Numeric(18, 8), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('rejection_reason', sa.String(500), nullable=True),
        sa.Column('execution_mode', sa.String(20), nullable=False, server_default='simulation'),
        sa.Column('broker_order_id', sa.String(100), nullable=True),
        sa.Column('broker_account_id', sa.String(100), nullable=True),
        sa.Column('underlying_symbol', sa.String(50), nullable=True),
        sa.Column('contract_type', sa.String(10), nullable=True),
        sa.Column('strike_price', sa.Numeric(18, 8), nullable=True),
        sa.Column('expiration_date', sa.Date(), nullable=True),
        sa.Column('contract_multiplier', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('filled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['signal_id'], ['signals.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['risk_decision_id'], ['risk_decisions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('signal_id'),
    )
    op.create_index('ix_paper_orders_strategy_created', 'paper_orders', ['strategy_id', 'created_at'])
    op.create_index('ix_paper_orders_symbol_status', 'paper_orders', ['symbol', 'status'])
    op.create_index('ix_paper_orders_status', 'paper_orders', ['status'])
    op.create_index(
        'ix_paper_orders_broker_order_id',
        'paper_orders',
        ['broker_order_id'],
        postgresql_where=sa.text('broker_order_id IS NOT NULL'),
    )

    # paper_fills
    op.create_table(
        'paper_fills',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('order_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('strategy_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('symbol', sa.String(50), nullable=False),
        sa.Column('side', sa.String(10), nullable=False),
        sa.Column('qty', sa.Numeric(18, 8), nullable=False),
        sa.Column('reference_price', sa.Numeric(18, 8), nullable=False),
        sa.Column('price', sa.Numeric(18, 8), nullable=False),
        sa.Column('gross_value', sa.Numeric(18, 2), nullable=False),
        sa.Column('fee', sa.Numeric(18, 2), nullable=False),
        sa.Column('slippage_bps', sa.Numeric(10, 4), nullable=False),
        sa.Column('slippage_amount', sa.Numeric(18, 2), nullable=False),
        sa.Column('net_value', sa.Numeric(18, 2), nullable=False),
        sa.Column('broker_fill_id', sa.String(100), nullable=True),
        sa.Column('broker_account_id', sa.String(100), nullable=True),
        sa.Column('filled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['order_id'], ['paper_orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_paper_fills_order_id', 'paper_fills', ['order_id'])
    op.create_index('ix_paper_fills_strategy_filled', 'paper_fills', ['strategy_id', 'filled_at'])
    op.create_index('ix_paper_fills_symbol_filled', 'paper_fills', ['symbol', 'filled_at'])


def downgrade() -> None:
    op.drop_index('ix_paper_fills_symbol_filled', table_name='paper_fills')
    op.drop_index('ix_paper_fills_strategy_filled', table_name='paper_fills')
    op.drop_index('ix_paper_fills_order_id', table_name='paper_fills')
    op.drop_table('paper_fills')
    op.drop_index('ix_paper_orders_broker_order_id', table_name='paper_orders')
    op.drop_index('ix_paper_orders_status', table_name='paper_orders')
    op.drop_index('ix_paper_orders_symbol_status', table_name='paper_orders')
    op.drop_index('ix_paper_orders_strategy_created', table_name='paper_orders')
    op.drop_table('paper_orders')
