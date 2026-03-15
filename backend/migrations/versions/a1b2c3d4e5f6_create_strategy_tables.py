"""create_strategy_tables

Revision ID: a1b2c3d4e5f6
Revises: 7a15366e61ae
Create Date: 2026-03-13 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '7a15366e61ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # strategies
    op.create_table(
        'strategies',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=2000), nullable=False, server_default=''),
        sa.Column('type', sa.String(length=20), nullable=False, server_default='config'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('current_version', sa.String(length=20), nullable=False, server_default='1.0.0'),
        sa.Column('market', sa.String(length=20), nullable=False),
        sa.Column('auto_pause_error_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_evaluated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key'),
    )
    op.create_index('ix_strategies_status', 'strategies', ['status'])
    op.create_index('ix_strategies_market_status', 'strategies', ['market', 'status'])
    op.create_index('ix_strategies_user_id', 'strategies', ['user_id'])

    # strategy_configs
    op.create_table(
        'strategy_configs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('strategy_id', sa.Uuid(), nullable=False),
        sa.Column('version', sa.String(length=20), nullable=False),
        sa.Column('config_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('strategy_id', 'version', name='uq_strategy_configs_strategy_version'),
    )
    op.create_index('ix_strategy_configs_strategy_active', 'strategy_configs', ['strategy_id', 'is_active'])

    # strategy_states
    op.create_table(
        'strategy_states',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('strategy_id', sa.Uuid(), nullable=False),
        sa.Column('state_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('strategy_id'),
    )

    # strategy_evaluations
    op.create_table(
        'strategy_evaluations',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('strategy_id', sa.Uuid(), nullable=False),
        sa.Column('strategy_version', sa.String(length=20), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('symbols_evaluated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('signals_emitted', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('exits_triggered', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('errors', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('duration_ms', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('skip_reason', sa.String(length=500), nullable=True),
        sa.Column('details_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_strategy_evaluations_strategy_at', 'strategy_evaluations', ['strategy_id', 'evaluated_at'])
    op.create_index('ix_strategy_evaluations_status', 'strategy_evaluations', ['status'])

    # position_overrides
    op.create_table(
        'position_overrides',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('position_id', sa.Uuid(), nullable=False),
        sa.Column('strategy_id', sa.Uuid(), nullable=False),
        sa.Column('override_type', sa.String(length=20), nullable=False),
        sa.Column('original_value_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('override_value_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('reason', sa.String(length=500), nullable=True),
        sa.Column('created_by', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_position_overrides_position_active', 'position_overrides', ['position_id', 'is_active'])
    op.create_index('ix_position_overrides_strategy_id', 'position_overrides', ['strategy_id'])


def downgrade() -> None:
    op.drop_table('position_overrides')
    op.drop_table('strategy_evaluations')
    op.drop_table('strategy_states')
    op.drop_table('strategy_configs')
    op.drop_table('strategies')
