"""add event_sections and extend event_pages

Revision ID: s7m8n9o0p1q2
Revises: r6l7m8n9o0p1
Create Date: 2026-06-22

擴充 event_pages（新增 category/venue/booking dates/banner/thumbnail）
新增 event_sections（活動區塊系統）
"""
from alembic import op
import sqlalchemy as sa

revision = 's7m8n9o0p1q2'
down_revision = 'r6l7m8n9o0p1'
branch_labels = None
depends_on = None


def upgrade():
    # ── 擴充 event_pages ──────────────────────────────────────────────────────
    op.add_column('event_pages', sa.Column('category',         sa.String(50),  nullable=True, server_default='concert'))
    op.add_column('event_pages', sa.Column('venue',            sa.String(200), nullable=True))
    op.add_column('event_pages', sa.Column('booking_open_at',  sa.DateTime,    nullable=True))
    op.add_column('event_pages', sa.Column('booking_close_at', sa.DateTime,    nullable=True))
    op.add_column('event_pages', sa.Column('banner_image',     sa.String(500), nullable=True))
    op.add_column('event_pages', sa.Column('thumbnail_image',  sa.String(500), nullable=True))

    # ── 新增 event_sections ───────────────────────────────────────────────────
    op.create_table(
        'event_sections',
        sa.Column('id',           sa.Integer,    primary_key=True),
        sa.Column('event_id',     sa.Integer,    sa.ForeignKey('event_pages.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('type',         sa.String(50), nullable=False),
        sa.Column('title',        sa.String(200), nullable=True),
        sa.Column('content_json', sa.Text,        nullable=True),
        sa.Column('sort_order',   sa.Integer,     nullable=False, server_default='0'),
        sa.Column('is_active',    sa.Boolean,     nullable=False, server_default='true'),
        sa.Column('created_at',   sa.DateTime,    nullable=True),
        sa.Column('updated_at',   sa.DateTime,    nullable=True),
    )


def downgrade():
    op.drop_table('event_sections')
    op.drop_column('event_pages', 'thumbnail_image')
    op.drop_column('event_pages', 'banner_image')
    op.drop_column('event_pages', 'booking_close_at')
    op.drop_column('event_pages', 'booking_open_at')
    op.drop_column('event_pages', 'venue')
    op.drop_column('event_pages', 'category')
