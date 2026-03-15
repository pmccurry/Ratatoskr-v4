"""create_observability_tables

Revision ID: h8c9d0e1f2a3
Revises: g7b8c9d0e1f2
Create Date: 2026-03-13 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'h8c9d0e1f2a3'
down_revision: Union[str, None] = 'g7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- audit_events ---
    op.create_table(
        'audit_events',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('category', sa.String(30), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('source_module', sa.String(50), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=True),
        sa.Column('entity_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('strategy_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('symbol', sa.String(50), nullable=True),
        sa.Column('summary', sa.String(500), nullable=False),
        sa.Column('details_json', sa.dialects.postgresql.JSON, nullable=True),
        sa.Column('ts', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
    )
    op.create_index('ix_audit_events_ts', 'audit_events', ['ts'])
    op.create_index('ix_audit_events_event_type_ts', 'audit_events', ['event_type', 'ts'])
    op.create_index('ix_audit_events_category_ts', 'audit_events', ['category', 'ts'])
    op.create_index('ix_audit_events_severity_ts', 'audit_events', ['severity', 'ts'])
    op.create_index('ix_audit_events_strategy_ts', 'audit_events', ['strategy_id', 'ts'],
                    postgresql_where=sa.text('strategy_id IS NOT NULL'))
    op.create_index('ix_audit_events_symbol_ts', 'audit_events', ['symbol', 'ts'],
                    postgresql_where=sa.text('symbol IS NOT NULL'))
    op.create_index('ix_audit_events_entity', 'audit_events', ['entity_type', 'entity_id'])

    # --- metric_datapoints ---
    op.create_table(
        'metric_datapoints',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('metric_name', sa.String(100), nullable=False),
        sa.Column('metric_type', sa.String(20), nullable=False),
        sa.Column('value', sa.Numeric(18, 4), nullable=False),
        sa.Column('labels_json', sa.dialects.postgresql.JSON, nullable=True),
        sa.Column('ts', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
    )
    op.create_index('ix_metric_datapoints_name_ts', 'metric_datapoints', ['metric_name', 'ts'])
    op.create_index('ix_metric_datapoints_ts', 'metric_datapoints', ['ts'])

    # --- alert_rules ---
    op.create_table(
        'alert_rules',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.String(1000), nullable=False),
        sa.Column('category', sa.String(20), nullable=False),
        sa.Column('condition_type', sa.String(30), nullable=False),
        sa.Column('condition_config', sa.dialects.postgresql.JSON, nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('enabled', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('cooldown_seconds', sa.Integer, nullable=False, server_default=sa.text('300')),
        sa.Column('notification_channels', sa.dialects.postgresql.JSON, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
    )

    # --- alert_instances ---
    op.create_table(
        'alert_instances',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('rule_id', sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('alert_rules.id', ondelete='CASCADE'), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('summary', sa.String(500), nullable=False),
        sa.Column('details_json', sa.dialects.postgresql.JSON, nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('triggered_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledged_by', sa.String(100), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notifications_sent', sa.dialects.postgresql.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
    )
    op.create_index('ix_alert_instances_status_triggered', 'alert_instances',
                    ['status', 'triggered_at'])
    op.create_index('ix_alert_instances_rule_triggered', 'alert_instances',
                    ['rule_id', 'triggered_at'])
    op.create_index('ix_alert_instances_severity_status', 'alert_instances',
                    ['severity', 'status'])


def downgrade() -> None:
    op.drop_index('ix_alert_instances_severity_status', table_name='alert_instances')
    op.drop_index('ix_alert_instances_rule_triggered', table_name='alert_instances')
    op.drop_index('ix_alert_instances_status_triggered', table_name='alert_instances')
    op.drop_table('alert_instances')

    op.drop_table('alert_rules')

    op.drop_index('ix_metric_datapoints_ts', table_name='metric_datapoints')
    op.drop_index('ix_metric_datapoints_name_ts', table_name='metric_datapoints')
    op.drop_table('metric_datapoints')

    op.drop_index('ix_audit_events_entity', table_name='audit_events')
    op.drop_index('ix_audit_events_symbol_ts', table_name='audit_events')
    op.drop_index('ix_audit_events_strategy_ts', table_name='audit_events')
    op.drop_index('ix_audit_events_severity_ts', table_name='audit_events')
    op.drop_index('ix_audit_events_category_ts', table_name='audit_events')
    op.drop_index('ix_audit_events_event_type_ts', table_name='audit_events')
    op.drop_index('ix_audit_events_ts', table_name='audit_events')
    op.drop_table('audit_events')
