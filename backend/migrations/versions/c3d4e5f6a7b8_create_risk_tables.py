"""create_risk_tables

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-13 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # risk_decisions
    op.create_table(
        'risk_decisions',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('signal_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('checks_passed', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('failed_check', sa.String(50), nullable=True),
        sa.Column('reason_code', sa.String(50), nullable=False),
        sa.Column('reason_text', sa.String(500), nullable=False),
        sa.Column('modifications_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('portfolio_state_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('ts', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['signal_id'], ['signals.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('signal_id'),
    )
    op.create_index('ix_risk_decisions_status_created', 'risk_decisions', ['status', 'created_at'])
    op.create_index('ix_risk_decisions_reason_code', 'risk_decisions', ['reason_code'])
    op.create_index('ix_risk_decisions_ts', 'risk_decisions', ['ts'])

    # kill_switches
    op.create_table(
        'kill_switches',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('scope', sa.String(20), nullable=False),
        sa.Column('strategy_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('activated_by', sa.String(30), nullable=True),
        sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deactivated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reason', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_kill_switches_scope_active', 'kill_switches', ['scope', 'is_active'])
    op.create_index('ix_kill_switches_strategy_active', 'kill_switches', ['strategy_id', 'is_active'])

    # risk_config
    op.create_table(
        'risk_config',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('max_position_size_percent', sa.Numeric(5, 2), nullable=False, server_default='10.0'),
        sa.Column('max_symbol_exposure_percent', sa.Numeric(5, 2), nullable=False, server_default='20.0'),
        sa.Column('max_strategy_exposure_percent', sa.Numeric(5, 2), nullable=False, server_default='30.0'),
        sa.Column('max_total_exposure_percent', sa.Numeric(5, 2), nullable=False, server_default='80.0'),
        sa.Column('max_drawdown_percent', sa.Numeric(5, 2), nullable=False, server_default='10.0'),
        sa.Column('max_drawdown_catastrophic_percent', sa.Numeric(5, 2), nullable=False, server_default='20.0'),
        sa.Column('max_daily_loss_percent', sa.Numeric(5, 2), nullable=False, server_default='3.0'),
        sa.Column('max_daily_loss_amount', sa.Numeric(12, 2), nullable=True),
        sa.Column('min_position_value', sa.Numeric(12, 2), nullable=False, server_default='100.0'),
        sa.Column('updated_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # risk_config_audit
    op.create_table(
        'risk_config_audit',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('field_changed', sa.String(100), nullable=False),
        sa.Column('old_value', sa.String(200), nullable=False),
        sa.Column('new_value', sa.String(200), nullable=False),
        sa.Column('changed_by', sa.String(100), nullable=False),
        sa.Column('changed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_risk_config_audit_changed_at', 'risk_config_audit', ['changed_at'])


def downgrade() -> None:
    op.drop_index('ix_risk_config_audit_changed_at', table_name='risk_config_audit')
    op.drop_table('risk_config_audit')
    op.drop_table('risk_config')
    op.drop_index('ix_kill_switches_strategy_active', table_name='kill_switches')
    op.drop_index('ix_kill_switches_scope_active', table_name='kill_switches')
    op.drop_table('kill_switches')
    op.drop_index('ix_risk_decisions_ts', table_name='risk_decisions')
    op.drop_index('ix_risk_decisions_reason_code', table_name='risk_decisions')
    op.drop_index('ix_risk_decisions_status_created', table_name='risk_decisions')
    op.drop_table('risk_decisions')
