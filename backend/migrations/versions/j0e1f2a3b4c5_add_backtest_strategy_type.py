"""add_backtest_strategy_type

Revision ID: j0e1f2a3b4c5
Revises: i9d0e1f2a3b4
Create Date: 2026-03-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'j0e1f2a3b4c5'
down_revision: Union[str, None] = 'i9d0e1f2a3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'backtest_runs',
        sa.Column('strategy_type', sa.String(20), nullable=False, server_default='conditions'),
    )
    op.add_column(
        'backtest_runs',
        sa.Column('strategy_file', sa.String(255), nullable=True),
    )
    op.alter_column('backtest_runs', 'strategy_id', nullable=True)


def downgrade() -> None:
    op.alter_column('backtest_runs', 'strategy_id', nullable=False)
    op.drop_column('backtest_runs', 'strategy_file')
    op.drop_column('backtest_runs', 'strategy_type')
