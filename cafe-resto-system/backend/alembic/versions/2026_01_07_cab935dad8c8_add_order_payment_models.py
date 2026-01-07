"""add_order_payment_models

Revision ID: cab935dad8c8
Revises: e40349bce913
Create Date: 2026-01-07 12:18:52.353145+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'cab935dad8c8'
down_revision = 'e40349bce913'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create order_status enum
    order_status_enum = postgresql.ENUM(
        'pending', 'in_progress', 'paid', 'completed', 'cancelled', 'voided',
        name='orderstatus'
    )
    order_status_enum.create(op.get_bind())

    # Create payment_intent_status enum
    payment_intent_status_enum = postgresql.ENUM(
        'created', 'processing', 'requires_action', 'succeeded', 'cancelled', 'failed',
        name='paymentintentstatus'
    )
    payment_intent_status_enum.create(op.get_bind())

    # Create payment_method enum
    payment_method_enum = postgresql.ENUM(
        'cash', 'card', 'terminal', 'qr', 'split',
        name='paymentmethod'
    )
    payment_method_enum.create(op.get_bind())

    # Create payment_status enum
    payment_status_enum = postgresql.ENUM(
        'pending', 'processing', 'completed', 'failed', 'refunded',
        name='paymentstatus'
    )
    payment_status_enum.create(op.get_bind())

    # Create refund_status enum
    refund_status_enum = postgresql.ENUM(
        'requested', 'processing', 'completed', 'failed',
        name='refundstatus'
    )
    refund_status_enum.create(op.get_bind())

    # Create receipt_type enum
    receipt_type_enum = postgresql.ENUM(
        'order', 'refund', 'payment', 'shift_report',
        name='receipttype'
    )
    receipt_type_enum.create(op.get_bind())

    # Create shift_status enum
    shift_status_enum = postgresql.ENUM(
        'opening', 'active', 'closing', 'closed', 'reconciled',
        name='shiftstatus'
    )
    shift_status_enum.create(op.get_bind())

    # Create cash_drawer_event_type enum
    cash_drawer_event_type_enum = postgresql.ENUM(
        'opening_balance', 'cash_drop', 'tip_payout', 'cash_shortage',
        'cash_adjustment', 'payment_in', 'change_out', 'petty_cash', 'other',
        name='cashdrawereventtype'
    )
    cash_drawer_event_type_enum.create(op.get_bind())

    # Create adjustment_type enum
    adjustment_type_enum = postgresql.ENUM(
        'comp', 'discount_percent', 'discount_amount', 'promo_code',
        'customer_reward', 'void', 'price_override', 'service_adjustment',
        'tax_adjustment', 'other',
        name='adjustmenttype'
    )
    adjustment_type_enum.create(op.get_bind())

    # Create orders table
    op.create_table(
        'orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('table_session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('server_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('draft_order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', order_status_enum, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('subtotal', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column('tax_amount', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column('discount_amount', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column('service_charge', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column('total_amount', sa.Numeric(12, 2), nullable=False, server_default='0.00'),
        sa.Column('tip_amount', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column('guest_count', sa.Integer(), nullable=True),
        sa.Column('guest_names', sa.String(500), nullable=True),
        sa.Column('special_requests', sa.String(2000), nullable=True),
        sa.Column('order_notes', sa.String(2000), nullable=True),
        sa.Column('is_rush', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('priority_level', sa.Integer(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['table_session_id'], ['table_sessions.id']),
        sa.ForeignKeyConstraint(['server_id'], ['users.id']),
        sa.ForeignKeyConstraint(['draft_order_id'], ['draft_orders.id']),
    )
    op.create_index('idx_order_tenant_id', 'orders', ['tenant_id'])
    op.create_index('idx_order_table_session_id', 'orders', ['table_session_id'])
    op.create_index('idx_order_server_id', 'orders', ['server_id'])
    op.create_index('idx_order_draft_order_id', 'orders', ['draft_order_id'])
    op.create_index('idx_order_status', 'orders', ['status'])
    op.create_index('idx_order_created_at', 'orders', ['created_at'])
    op.create_index('idx_order_is_rush', 'orders', ['is_rush'])
    op.create_index('idx_order_priority_level', 'orders', ['priority_level'])
    op.create_index('idx_order_completed_at', 'orders', ['completed_at'])

    # Create order_line_items table
    op.create_table(
        'order_line_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('menu_item_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('unit_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('price_at_order', sa.Numeric(10, 2), nullable=False),
        sa.Column('line_total', sa.Numeric(10, 2), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.String(2000), nullable=True),
        sa.Column('special_instructions', sa.String(500), nullable=True),
        sa.Column('modifiers', postgresql.JSON, nullable=True),
        sa.Column('discount_amount', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column('discount_percentage', sa.Numeric(5, 2), nullable=True),
        sa.Column('is_comped', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_voided', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('parent_item_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.ForeignKeyConstraint(['menu_item_id'], ['menu_items.id']),
        sa.ForeignKeyConstraint(['parent_item_id'], ['order_line_items.id']),
    )
    op.create_index('idx_order_line_item_tenant_id', 'order_line_items', ['tenant_id'])
    op.create_index('idx_order_line_item_order_id', 'order_line_items', ['order_id'])
    op.create_index('idx_order_line_item_menu_item_id', 'order_line_items', ['menu_item_id'])

    # Create payment_intents table
    op.create_table(
        'payment_intents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('status', payment_intent_status_enum, nullable=False),
        sa.Column('payment_method', payment_method_enum, nullable=True),
        sa.Column('client_secret', sa.String(500), nullable=True),
        sa.Column('payment_intent_reference', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', postgresql.JSON, nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
    )
    op.create_index('idx_payment_intent_tenant_id', 'payment_intents', ['tenant_id'])
    op.create_index('idx_payment_intent_order_id', 'payment_intents', ['order_id'])
    op.create_index('idx_payment_intent_status', 'payment_intents', ['status'])
    op.create_index('idx_payment_intent_created_at', 'payment_intents', ['created_at'])

    # Create payments table
    op.create_table(
        'payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('payment_intent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('method', payment_method_enum, nullable=False),
        sa.Column('status', payment_status_enum, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('refunded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('card_last_4', sa.String(4), nullable=True),
        sa.Column('card_holder_name', sa.String(100), nullable=True),
        sa.Column('terminal_reference_id', sa.String(50), nullable=True),
        sa.Column('terminal_response', postgresql.JSON, nullable=True),
        sa.Column('qr_code', sa.String(255), nullable=True),
        sa.Column('qr_provider', sa.String(50), nullable=True),
        sa.Column('processing_fee', sa.Numeric(10, 2), nullable=True),
        sa.Column('metadata', postgresql.JSON, nullable=True),
        sa.Column('refund_of_payment_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('processed_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.String(500), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.ForeignKeyConstraint(['payment_intent_id'], ['payment_intents.id']),
        sa.ForeignKeyConstraint(['refund_of_payment_id'], ['payments.id']),
        sa.ForeignKeyConstraint(['processed_by_user_id'], ['users.id']),
    )
    op.create_index('idx_payment_tenant_id', 'payments', ['tenant_id'])
    op.create_index('idx_payment_order_id', 'payments', ['order_id'])
    op.create_index('idx_payment_method', 'payments', ['method'])
    op.create_index('idx_payment_status', 'payments', ['status'])
    op.create_index('idx_payment_created_at', 'payments', ['created_at'])
    op.create_index('idx_payment_processed_at', 'payments', ['processed_at'])

    # Create refunds table
    op.create_table(
        'refunds',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('status', refund_status_enum, nullable=False),
        sa.Column('reason', sa.String(500), nullable=False),
        sa.Column('notes', sa.String(1000), nullable=True),
        sa.Column('processed_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('authorized_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('refund_reference_id', sa.String(255), nullable=True),
        sa.Column('external_refund_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id']),
        sa.ForeignKeyConstraint(['processed_by'], ['users.id']),
        sa.ForeignKeyConstraint(['authorized_by'], ['users.id']),
    )
    op.create_index('idx_refund_tenant_id', 'refunds', ['tenant_id'])
    op.create_index('idx_refund_order_id', 'refunds', ['order_id'])
    op.create_index('idx_refund_payment_id', 'refunds', ['payment_id'])
    op.create_index('idx_refund_status', 'refunds', ['status'])
    op.create_index('idx_refund_created_at', 'refunds', ['created_at'])

    # Create order_payments join table
    op.create_table(
        'order_payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('allocated_amount', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id']),
        sa.UniqueConstraint('payment_id'),
    )
    op.create_index('idx_order_payment_order_id', 'order_payments', ['order_id'])
    op.create_index('idx_order_payment_payment_id', 'order_payments', ['payment_id'])

    # Create receipts table
    op.create_table(
        'receipts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('refund_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('shift_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('receipt_type', receipt_type_enum, nullable=False),
        sa.Column('receipt_number', sa.String(50), nullable=False),
        sa.Column('printed_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('printed_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reprinted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reprint_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('printed_to_printer', sa.String(100), nullable=True),
        sa.Column('receipt_data', postgresql.JSON, nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.ForeignKeyConstraint(['refund_id'], ['refunds.id']),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id']),
        sa.ForeignKeyConstraint(['shift_id'], ['shifts.id']),
        sa.ForeignKeyConstraint(['printed_by'], ['users.id']),
    )
    op.create_index('idx_receipt_tenant_id', 'receipts', ['tenant_id'])
    op.create_index('idx_receipt_order_id', 'receipts', ['order_id'])
    op.create_index('idx_receipt_refund_id', 'receipts', ['refund_id'])
    op.create_index('idx_receipt_shift_id', 'receipts', ['shift_id'])
    op.create_index('idx_receipt_receipt_number', 'receipts', ['receipt_number'])
    op.create_index('idx_receipt_printed_at', 'receipts', ['printed_at'])

    # Create shifts table
    op.create_table(
        'shifts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('server_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('location_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', shift_status_enum, nullable=False),
        sa.Column('opened_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reconciled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('opening_balance', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column('cash_sales', sa.Numeric(12, 2), nullable=False, server_default='0.00'),
        sa.Column('card_sales', sa.Numeric(12, 2), nullable=False, server_default='0.00'),
        sa.Column('tip_sales', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column('closing_cash_count', sa.Numeric(12, 2), nullable=True),
        sa.Column('card_count', sa.Numeric(12, 2), nullable=True),
        sa.Column('expected_cash', sa.Numeric(12, 2), nullable=True),
        sa.Column('cash_variance', sa.Numeric(10, 2), nullable=True),
        sa.Column('is_over', sa.Boolean(), nullable=True),
        sa.Column('total_break_time_minutes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('break_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('opening_notes', sa.String(1000), nullable=True),
        sa.Column('closing_notes', sa.String(1000), nullable=True),
        sa.Column('reconciliation_notes', sa.String(1000), nullable=True),
        sa.Column('opened_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('closed_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reconciled_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['server_id'], ['users.id']),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id']),
        sa.ForeignKeyConstraint(['opened_by'], ['users.id']),
        sa.ForeignKeyConstraint(['closed_by'], ['users.id']),
        sa.ForeignKeyConstraint(['reconciled_by'], ['users.id']),
    )
    op.create_index('idx_shift_tenant_id', 'shifts', ['tenant_id'])
    op.create_index('idx_shift_server_id', 'shifts', ['server_id'])
    op.create_index('idx_shift_location_id', 'shifts', ['location_id'])
    op.create_index('idx_shift_status', 'shifts', ['status'])
    op.create_index('idx_shift_opened_at', 'shifts', ['opened_at'])
    op.create_index('idx_shift_closed_at', 'shifts', ['closed_at'])
    op.create_index('idx_shift_opening_balance', 'shifts', ['opening_balance'])

    # Create cash_drawer_events table
    op.create_table(
        'cash_drawer_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('shift_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('location_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', cash_drawer_event_type_enum, nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column('balance_after', sa.Numeric(12, 2), nullable=False, server_default='0.00'),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('description', sa.String(500), nullable=False),
        sa.Column('reason', sa.String(500), nullable=True),
        sa.Column('performed_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('metadata', postgresql.JSON, nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['shift_id'], ['shifts.id']),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id']),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id']),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.ForeignKeyConstraint(['performed_by'], ['users.id']),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id']),
    )
    op.create_index('idx_cash_drawer_tenant_id', 'cash_drawer_events', ['tenant_id'])
    op.create_index('idx_cash_drawer_shift_id', 'cash_drawer_events', ['shift_id'])
    op.create_index('idx_cash_drawer_location_id', 'cash_drawer_events', ['location_id'])
    op.create_index('idx_cash_drawer_event_type', 'cash_drawer_events', ['event_type'])
    op.create_index('idx_cash_drawer_payment_id', 'cash_drawer_events', ['payment_id'])
    op.create_index('idx_cash_drawer_order_id', 'cash_drawer_events', ['order_id'])
    op.create_index('idx_cash_drawer_occurred_at', 'cash_drawer_events', ['occurred_at'])
    op.create_index('idx_cash_drawer_performed_by', 'cash_drawer_events', ['performed_by'])

    # Create order_adjustments table
    op.create_table(
        'order_adjustments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('order_line_item_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('adjustment_type', adjustment_type_enum, nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False, server_default='0.00'),
        sa.Column('percentage', sa.Numeric(5, 2), nullable=True),
        sa.Column('original_amount', sa.Numeric(10, 2), nullable=True),
        sa.Column('new_amount', sa.Numeric(10, 2), nullable=True),
        sa.Column('reason', sa.String(500), nullable=False),
        sa.Column('notes', sa.String(1000), nullable=True),
        sa.Column('authorized_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('requires_manager_approval', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_visible_to_customer', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('display_name', sa.String(100), nullable=True),
        sa.Column('promo_code', sa.String(50), nullable=True),
        sa.Column('applied_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('applied_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
        sa.ForeignKeyConstraint(['order_line_item_id'], ['order_line_items.id']),
        sa.ForeignKeyConstraint(['authorized_by'], ['users.id']),
        sa.ForeignKeyConstraint(['applied_by'], ['users.id']),
    )
    op.create_index('idx_adjustment_tenant_id', 'order_adjustments', ['tenant_id'])
    op.create_index('idx_adjustment_order_id', 'order_adjustments', ['order_id'])
    op.create_index('idx_adjustment_order_line_item_id', 'order_adjustments', ['order_line_item_id'])
    op.create_index('idx_adjustment_type', 'order_adjustments', ['adjustment_type'])
    op.create_index('idx_adjustment_applied_at', 'order_adjustments', ['applied_at'])
    op.create_index('idx_adjustment_authorized_by', 'order_adjustments', ['authorized_by'])
    op.create_index('idx_adjustment_promo_code', 'order_adjustments', ['promo_code'])


def downgrade() -> None:
    # Drop tables in reverse order (to respect FK constraints)
    op.drop_table('order_adjustments')
    op.drop_table('cash_drawer_events')
    op.drop_table('shifts')
    op.drop_table('receipts')
    op.drop_table('order_payments')
    op.drop_table('refunds')
    op.drop_table('payments')
    op.drop_table('payment_intents')
    op.drop_table('order_line_items')
    op.drop_table('orders')

    # Drop enums
    adjustment_type_enum = postgresql.ENUM(name='adjustmenttype')
    adjustment_type_enum.drop(op.get_bind())

    cash_drawer_event_type_enum = postgresql.ENUM(name='cashdrawereventtype')
    cash_drawer_event_type_enum.drop(op.get_bind())

    shift_status_enum = postgresql.ENUM(name='shiftstatus')
    shift_status_enum.drop(op.get_bind())

    receipt_type_enum = postgresql.ENUM(name='receipttype')
    receipt_type_enum.drop(op.get_bind())

    refund_status_enum = postgresql.ENUM(name='refundstatus')
    refund_status_enum.drop(op.get_bind())

    payment_status_enum = postgresql.ENUM(name='paymentstatus')
    payment_status_enum.drop(op.get_bind())

    payment_method_enum = postgresql.ENUM(name='paymentmethod')
    payment_method_enum.drop(op.get_bind())

    payment_intent_status_enum = postgresql.ENUM(name='paymentintentstatus')
    payment_intent_status_enum.drop(op.get_bind())

    order_status_enum = postgresql.ENUM(name='orderstatus')
    order_status_enum.drop(op.get_bind())
