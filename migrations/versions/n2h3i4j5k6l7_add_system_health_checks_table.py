"""add system_health_checks table

Revision ID: n2h3i4j5k6l7
Revises: m1g2h3i4j5k6
Create Date: 2026-06-21

"""
from alembic import op
import sqlalchemy as sa

revision = 'n2h3i4j5k6l7'
down_revision = 'm1g2h3i4j5k6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'system_health_checks',
        sa.Column('id',              sa.Integer(),    nullable=False),
        sa.Column('component_name',  sa.String(100),  nullable=False),
        sa.Column('status',          sa.String(20),   nullable=False, server_default='UNKNOWN'),
        sa.Column('response_time',   sa.Float(),      nullable=True),
        sa.Column('last_checked_at', sa.DateTime(),   nullable=True),
        sa.Column('message',         sa.Text(),       nullable=True),
        sa.Column('created_at',      sa.DateTime(),   nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('component_name', name='uq_system_health_component_name'),
    )
    op.create_index('ix_system_health_checks_component_name',
                    'system_health_checks', ['component_name'])


def downgrade():
    op.drop_index('ix_system_health_checks_component_name',
                  table_name='system_health_checks')
    op.drop_table('system_health_checks')
