"""add crawler_source_status table

Revision ID: m1g2h3i4j5k6
Revises: l0f1a2b3c4d5
Create Date: 2026-06-21

"""
from alembic import op
import sqlalchemy as sa

revision = 'm1g2h3i4j5k6'
down_revision = 'l0f1a2b3c4d5'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'crawler_source_status',
        sa.Column('id',              sa.Integer(),    nullable=False),
        sa.Column('source_name',     sa.String(100),  nullable=False),
        sa.Column('crawler_enabled', sa.Boolean(),    nullable=False, server_default='false'),
        sa.Column('last_run_at',     sa.DateTime(),   nullable=True),
        sa.Column('raw_count',       sa.Integer(),    nullable=False, server_default='0'),
        sa.Column('imported_count',  sa.Integer(),    nullable=False, server_default='0'),
        sa.Column('skipped_count',   sa.Integer(),    nullable=False, server_default='0'),
        sa.Column('coverage_status', sa.String(20),   nullable=False, server_default='NONE'),
        sa.Column('created_at',      sa.DateTime(),   nullable=True),
        sa.Column('updated_at',      sa.DateTime(),   nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_name', name='uq_crawler_source_status_name'),
    )


def downgrade():
    op.drop_table('crawler_source_status')
