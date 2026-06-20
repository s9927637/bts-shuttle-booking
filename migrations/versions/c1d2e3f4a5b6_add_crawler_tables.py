"""add crawler tables

Revision ID: c1d2e3f4a5b6
Revises: b2c3d4e5f6a7
Create Date: 2026-06-20

新增 crawl_jobs / crawl_logs 資料表。
新增 crawler_hash、scheduler_enabled、last_success_at 至 concerts。
不影響任何既有資料表欄位。完整可 rollback。
"""
from alembic import op
import sqlalchemy as sa

revision = 'c1d2e3f4a5b6'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    # ── crawl_jobs ───────────────────────────────────────────────────────────
    op.create_table(
        'crawl_jobs',
        sa.Column('id',               sa.Integer(),    primary_key=True),
        sa.Column('source_name',      sa.String(100),  nullable=False),
        sa.Column('status',           sa.String(20),   nullable=False, server_default='pending'),
        sa.Column('started_at',       sa.DateTime(),   nullable=True),
        sa.Column('finished_at',      sa.DateTime(),   nullable=True),
        sa.Column('created_count',    sa.Integer(),    nullable=False, server_default='0'),
        sa.Column('updated_count',    sa.Integer(),    nullable=False, server_default='0'),
        sa.Column('skipped_count',    sa.Integer(),    nullable=False, server_default='0'),
        sa.Column('error_count',      sa.Integer(),    nullable=False, server_default='0'),
        sa.Column('created_at',       sa.DateTime(),   nullable=True),
        sa.Column('scheduler_enabled', sa.Boolean(),   nullable=False, server_default='false'),
        sa.Column('last_success_at',  sa.DateTime(),   nullable=True),
    )

    # ── crawl_logs ───────────────────────────────────────────────────────────
    op.create_table(
        'crawl_logs',
        sa.Column('id',          sa.Integer(),    primary_key=True),
        sa.Column('job_id',      sa.Integer(),    sa.ForeignKey('crawl_jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_name', sa.String(100),  nullable=False),
        sa.Column('level',       sa.String(10),   nullable=False, server_default='INFO'),
        sa.Column('message',     sa.Text(),       nullable=False),
        sa.Column('created_at',  sa.DateTime(),   nullable=True),
    )
    op.create_index('ix_crawl_logs_job_id',    'crawl_logs', ['job_id'])
    op.create_index('ix_crawl_logs_created_at', 'crawl_logs', ['created_at'])

    # ── 新增欄位至 concerts（不修改現有欄位）───────────────────────────────
    op.add_column('concerts', sa.Column('crawler_hash',      sa.String(64),  nullable=True))
    op.add_column('concerts', sa.Column('scheduler_enabled', sa.Boolean(),   nullable=True, server_default='false'))
    op.add_column('concerts', sa.Column('last_success_at',   sa.DateTime(),  nullable=True))
    op.create_index('ix_concerts_crawler_hash', 'concerts', ['crawler_hash'], unique=True)


def downgrade():
    op.drop_index('ix_concerts_crawler_hash', table_name='concerts')
    op.drop_column('concerts', 'last_success_at')
    op.drop_column('concerts', 'scheduler_enabled')
    op.drop_column('concerts', 'crawler_hash')

    op.drop_index('ix_crawl_logs_created_at', table_name='crawl_logs')
    op.drop_index('ix_crawl_logs_job_id',     table_name='crawl_logs')
    op.drop_table('crawl_logs')
    op.drop_table('crawl_jobs')
