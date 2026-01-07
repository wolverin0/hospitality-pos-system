"""Initial migration with tenant table and RLS setup

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-01-06

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001_initial_schema'
down_revision = None


def upgrade():
    # Create tenants table
    op.create_table(
        'tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('slug', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('email', sa.String(255), nullable=False, index=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('settings', sa.Text(), nullable=True),
        sa.Column('plan', sa.String(50), nullable=False, server_default='basic'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true', index=True),
    )
    
    # Create indexes for tenant table
    op.create_index('idx_tenant_slug', 'tenants', ['slug'])
    op.create_index('idx_tenant_is_active', 'tenants', ['is_active'])
    
    # Enable Row Level Security on tenants table
    op.execute('ALTER TABLE tenants ENABLE ROW LEVEL SECURITY')
    
    # Create policy for tenant isolation (all users can see all tenants for now)
    # In production, this would be restricted
    op.execute("""
        CREATE POLICY tenant_isolation ON tenants
        FOR ALL
        USING (true)
        WITH CHECK (true);
    """)


def downgrade():
    # Drop RLS policies
    op.execute('DROP POLICY IF EXISTS tenant_isolation ON tenants')
    
    # Disable RLS
    op.execute('ALTER TABLE tenants DISABLE ROW LEVEL SECURITY')
    
    # Drop indexes
    op.drop_index('idx_tenant_is_active', 'tenants')
    op.drop_index('idx_tenant_slug', 'tenants')
    
    # Drop tenants table
    op.drop_table('tenants')
