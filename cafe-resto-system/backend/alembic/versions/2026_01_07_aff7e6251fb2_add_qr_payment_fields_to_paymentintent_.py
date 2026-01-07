"""Add QR payment fields to PaymentIntent and PARTIALLY_PAID to OrderStatus

Revision ID: aff7e6251fb2
Revises: cab935dad8c8
Create Date: 2026-01-07 14:39:35.481750+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'aff7e6251fb2'
down_revision = 'cab935dad8c8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
