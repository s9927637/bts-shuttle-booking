"""add crawler_audit_logs table

Revision ID: r6l7m8n9o0p1
Revises: q5k6l7m8n9o0
Create Date: 2026-06-21
"""
from alembic import op
import sqlalchemy as sa

revision = 'r6l7m8n9o0p1'
down_revision = 'q5k6l7m8n9o0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'crawler_audit_logs',
        sa.Column('id',          sa.Integer(),    primary_key=True),
        sa.Column('job_id',      sa.Integer(),    sa.ForeignKey('crawl_jobs.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('source_name', sa.String(50),   nullable=False, index=True),
        sa.Column('event_name',  sa.String(300),  nullable=True),
        sa.Column('artist_name', sa.String(150),  nullable=True),
        sa.Column('event_date',  sa.Date(),       nullable=True),
        sa.Column('venue',       sa.String(200),  nullable=True),
        sa.Column('city',        sa.String(50),   nullable=True),
        sa.Column('source_url',  sa.String(500),  nullable=True),
        sa.Column('status',      sa.String(20),   nullable=False, index=True),
        sa.Column('reason',      sa.String(50),   nullable=True,  index=True),
        sa.Column('created_at',  sa.DateTime(),   nullable=True,  index=True),
    )


def downgrade():
    op.drop_table('crawler_audit_logs')
