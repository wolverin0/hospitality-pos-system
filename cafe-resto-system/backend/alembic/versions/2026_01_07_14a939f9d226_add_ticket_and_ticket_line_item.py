"""add_ticket_and_ticket_line_item

Revision ID: 14a939f9d226
Revises: 9dfb6218bc5d
Create Date: 2026-01-07 02:09:23.733824+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '14a939f9d226'
down_revision = '9dfb6218bc5d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create tickets table
    op.create_table(
        'tickets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('draft_order_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('table_session_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('station_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='new', index=True),
        sa.Column('course_number', sa.Integer(), nullable=False, server_default='0', index=True),
        sa.Column('course_name', sa.String(255), nullable=True),
        sa.Column('is_rush', sa.Boolean(), nullable=False, server_default='false', index=True),
        sa.Column('priority_level', sa.Integer(), nullable=True),
        sa.Column('estimated_prep_time_minutes', sa.Integer(), nullable=True),
        sa.Column('prep_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ready_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('table_number', sa.String(50), nullable=True),
        sa.Column('server_name', sa.String(255), nullable=True),
        sa.Column('special_instructions', sa.String(2000), nullable=True),
        sa.Column('is_held', sa.Boolean(), nullable=False, server_default='false', index=True),
        sa.Column('held_reason', sa.String(500), nullable=True),
        sa.Column('held_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('print_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_printed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('fired_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('voided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('voided_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('voided_reason', sa.String(500), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['draft_order_id'], ['draft_orders.id']),
        sa.ForeignKeyConstraint(['table_session_id'], ['table_sessions.id']),
        sa.ForeignKeyConstraint(['station_id'], ['menu_stations.id']),
        sa.ForeignKeyConstraint(['voided_by'], ['users.id']),
    )

    # Create indexes for tickets table
    op.create_index('idx_ticket_tenant_id', 'tickets', ['tenant_id'])
    op.create_index('idx_ticket_draft_order_id', 'tickets', ['draft_order_id'])
    op.create_index('idx_ticket_table_session_id', 'tickets', ['table_session_id'])
    op.create_index('idx_ticket_station_id', 'tickets', ['station_id'])
    op.create_index('idx_ticket_status', 'tickets', ['status'])
    op.create_index('idx_ticket_course_number', 'tickets', ['course_number'])
    op.create_index('idx_ticket_is_rush', 'tickets', ['is_rush'])
    op.create_index('idx_ticket_is_held', 'tickets', ['is_held'])
    op.create_index('idx_ticket_created_at', 'tickets', ['created_at'])

    # Create ticket_line_items table
    op.create_table(
        'ticket_line_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('ticket_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('menu_item_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.String(2000), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('price_at_order', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column('line_total', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column('course_number', sa.Integer(), nullable=False, server_default='0', index=True),
        sa.Column('course_name', sa.String(255), nullable=True),
        sa.Column('fired_status', sa.String(50), nullable=False, server_default='pending', index=True),
        sa.Column('fired_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('held_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('held_reason', sa.String(500), nullable=True),
        sa.Column('voided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('voided_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('voided_reason', sa.String(500), nullable=True),
        sa.Column('preparation_status', sa.String(50), nullable=False, server_default='pending', index=True),
        sa.Column('preparation_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('preparation_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('special_instructions', sa.String(1000), nullable=True),
        sa.Column('modifiers', postgresql.JSON(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('parent_line_item_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id']),
        sa.ForeignKeyConstraint(['menu_item_id'], ['menu_items.id']),
        sa.ForeignKeyConstraint(['voided_by'], ['users.id']),
        sa.ForeignKeyConstraint(['parent_line_item_id'], ['ticket_line_items.id']),
    )

    # Create indexes for ticket_line_items table
    op.create_index('idx_ticket_line_item_tenant_id', 'ticket_line_items', ['tenant_id'])
    op.create_index('idx_ticket_line_item_ticket_id', 'ticket_line_items', ['ticket_id'])
    op.create_index('idx_ticket_line_item_menu_item_id', 'ticket_line_items', ['menu_item_id'])
    op.create_index('idx_ticket_line_item_fired_status', 'ticket_line_items', ['fired_status'])
    op.create_index('idx_ticket_line_item_course_number', 'ticket_line_items', ['course_number'])
    op.create_index('idx_ticket_line_item_preparation_status', 'ticket_line_items', ['preparation_status'])
    op.create_index('idx_ticket_line_item_parent_line_item_id', 'ticket_line_items', ['parent_line_item_id'])
    op.create_index('idx_ticket_line_item_sort_order', 'ticket_line_items', ['sort_order'])


def downgrade() -> None:
    # Drop indexes for ticket_line_items table
    op.drop_index('idx_ticket_line_item_sort_order', 'ticket_line_items')
    op.drop_index('idx_ticket_line_item_parent_line_item_id', 'ticket_line_items')
    op.drop_index('idx_ticket_line_item_preparation_status', 'ticket_line_items')
    op.drop_index('idx_ticket_line_item_course_number', 'ticket_line_items')
    op.drop_index('idx_ticket_line_item_fired_status', 'ticket_line_items')
    op.drop_index('idx_ticket_line_item_menu_item_id', 'ticket_line_items')
    op.drop_index('idx_ticket_line_item_ticket_id', 'ticket_line_items')
    op.drop_index('idx_ticket_line_item_tenant_id', 'ticket_line_items')

    # Drop ticket_line_items table
    op.drop_table('ticket_line_items')

    # Drop indexes for tickets table
    op.drop_index('idx_ticket_created_at', 'tickets')
    op.drop_index('idx_ticket_is_held', 'tickets')
    op.drop_index('idx_ticket_is_rush', 'tickets')
    op.drop_index('idx_ticket_course_number', 'tickets')
    op.drop_index('idx_ticket_status', 'tickets')
    op.drop_index('idx_ticket_station_id', 'tickets')
    op.drop_index('idx_ticket_table_session_id', 'tickets')
    op.drop_index('idx_ticket_draft_order_id', 'tickets')
    op.drop_index('idx_ticket_tenant_id', 'tickets')

    # Drop tickets table
    op.drop_table('tickets')
