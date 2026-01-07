"""add_version_field_to_tickets

Revision ID: e40349bce913
Revises: 14a939f9d226
Create Date: 2026-01-07 02:31:01.249835+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'e40349bce913'
down_revision = '14a939f9d226'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add version column to tickets table
    op.add_column('tickets', 'version', sa.Integer(), server_default='0', nullable=False)

    # Add version column to ticket_line_items table
    op.add_column('ticket_line_items', 'version', sa.Integer(), server_default='0', nullable=False)


def downgrade() -> None:
    # Drop version columns
    op.drop_column('ticket_line_items', 'version')
    op.drop_column('tickets', 'version')
