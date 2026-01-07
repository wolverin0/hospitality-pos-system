"""add_menu_station_and_kitchen_course

Revision ID: 9dfb6218bc5d
Revises: 001_initial_schema
Create Date: 2026-01-07 01:56:11.425380+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '9dfb6218bc5d'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add columns to menu_items table for station and course
    op.add_column('menu_items',
        sa.Column('station_id', postgresql.UUID(as_uuid=True), nullable=True, index=True)
    )
    op.add_column('menu_items',
        sa.Column('course_id', postgresql.UUID(as_uuid=True), nullable=True, index=True)
    )
    op.add_column('menu_items',
        sa.Column('default_prep_time_minutes', sa.Integer(), nullable=True)
    )

    # Create foreign key constraints for menu_items
    op.create_foreign_key('fk_menu_items_station_id', 'menu_items', 'menu_stations', ['station_id'], ['id'])
    op.create_foreign_key('fk_menu_items_course_id', 'menu_items', 'kitchen_courses', ['course_id'], ['id'])

    # Create indexes for menu_items new columns
    op.create_index('idx_menu_item_station_id', 'menu_items', ['station_id'])
    op.create_index('idx_menu_item_course_id', 'menu_items', ['course_id'])

    # Create menu_stations table
    op.create_table(
        'menu_stations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('location_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('station_type', sa.String(50), nullable=False, server_default='kitchen', index=True),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('color', sa.String(7), nullable=True),
        sa.Column('icon', sa.String(50), nullable=True),
        sa.Column('filter_item_types', sa.String(500), nullable=True),
        sa.Column('filter_category_ids', sa.String(2000), nullable=True),
        sa.Column('filter_custom_rules', sa.String(2000), nullable=True),
        sa.Column('printer_ids', sa.String(1000), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true', index=True),
        sa.Column('is_visible_in_kds', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('requires_expo_approval', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id']),
    )

    # Create indexes for menu_stations table
    op.create_index('idx_menu_station_tenant_id', 'menu_stations', ['tenant_id'])
    op.create_index('idx_menu_station_location_id', 'menu_stations', ['location_id'])
    op.create_index('idx_menu_station_station_type', 'menu_stations', ['station_type'])
    op.create_index('idx_menu_station_is_active', 'menu_stations', ['is_active'])
    op.create_index('idx_menu_station_display_order', 'menu_stations', ['display_order'])

    # Create kitchen_courses table
    op.create_table(
        'kitchen_courses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('location_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('station_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('course_type', sa.String(50), nullable=False, server_default='mains', index=True),
        sa.Column('course_number', sa.Integer(), nullable=False, server_default='0', index=True),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('color', sa.String(7), nullable=True),
        sa.Column('icon', sa.String(50), nullable=True),
        sa.Column('auto_fire_on_confirm', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('default_prep_time_minutes', sa.Integer(), nullable=True),
        sa.Column('filter_item_types', sa.String(500), nullable=True),
        sa.Column('filter_category_ids', sa.String(2000), nullable=True),
        sa.Column('filter_custom_rules', sa.String(2000), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true', index=True),
        sa.Column('is_visible_in_menu', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id']),
        sa.ForeignKeyConstraint(['station_id'], ['menu_stations.id']),
    )

    # Create indexes for kitchen_courses table
    op.create_index('idx_kitchen_course_tenant_id', 'kitchen_courses', ['tenant_id'])
    op.create_index('idx_kitchen_course_location_id', 'kitchen_courses', ['location_id'])
    op.create_index('idx_kitchen_course_station_id', 'kitchen_courses', ['station_id'])
    op.create_index('idx_kitchen_course_course_type', 'kitchen_courses', ['course_type'])
    op.create_index('idx_kitchen_course_course_number', 'kitchen_courses', ['course_number'])
    op.create_index('idx_kitchen_course_is_active', 'kitchen_courses', ['is_active'])


def downgrade() -> None:
    # Drop indexes for menu_items new columns
    op.drop_index('idx_menu_item_course_id', 'menu_items')
    op.drop_index('idx_menu_item_station_id', 'menu_items')

    # Drop foreign keys for menu_items
    op.drop_constraint('fk_menu_items_course_id', 'menu_items', type_='foreignkey')
    op.drop_constraint('fk_menu_items_station_id', 'menu_items', type_='foreignkey')

    # Drop columns from menu_items table
    op.drop_column('menu_items', 'default_prep_time_minutes')
    op.drop_column('menu_items', 'course_id')
    op.drop_column('menu_items', 'station_id')

    # Drop indexes for kitchen_courses table
    op.drop_index('idx_kitchen_course_is_active', 'kitchen_courses')
    op.drop_index('idx_kitchen_course_course_number', 'kitchen_courses')
    op.drop_index('idx_kitchen_course_course_type', 'kitchen_courses')
    op.drop_index('idx_kitchen_course_station_id', 'kitchen_courses')
    op.drop_index('idx_kitchen_course_location_id', 'kitchen_courses')
    op.drop_index('idx_kitchen_course_tenant_id', 'kitchen_courses')

    # Drop kitchen_courses table
    op.drop_table('kitchen_courses')

    # Drop indexes for menu_stations table
    op.drop_index('idx_menu_station_display_order', 'menu_stations')
    op.drop_index('idx_menu_station_is_active', 'menu_stations')
    op.drop_index('idx_menu_station_station_type', 'menu_stations')
    op.drop_index('idx_menu_station_location_id', 'menu_stations')
    op.drop_index('idx_menu_station_tenant_id', 'menu_stations')

    # Drop menu_stations table
    op.drop_table('menu_stations')
