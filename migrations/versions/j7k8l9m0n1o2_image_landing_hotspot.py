"""V1 Architecture Refactor: Landing Page = Image + Hotspot

landing_html/css/js 標記為 Deprecated（保留欄位供 BTS 向前相容，不刪除）。
新增 landing_image_desktop/tablet/mobile + landing_published + event_hotspots。

Revision ID: j7k8l9m0n1o2
Revises: i6j7k8l9m0n1
Create Date: 2026-07-07
"""
from alembic import op
import sqlalchemy as sa

revision = 'j7k8l9m0n1o2'
down_revision = 'i6j7k8l9m0n1'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('event_pages', sa.Column('landing_image_desktop', sa.String(length=500), nullable=True))
    op.add_column('event_pages', sa.Column('landing_image_tablet', sa.String(length=500), nullable=True))
    op.add_column('event_pages', sa.Column('landing_image_mobile', sa.String(length=500), nullable=True))
    op.add_column('event_pages', sa.Column('landing_published', sa.Boolean(), nullable=True))

    op.create_table(
        'event_hotspots',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('event_id', sa.Integer(), sa.ForeignKey('event_pages.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('label', sa.String(length=100), nullable=False),
        sa.Column('link_type', sa.String(length=20), nullable=False, server_default='booking'),
        sa.Column('custom_url', sa.String(length=500), nullable=True),
        sa.Column('x_pct', sa.Float(), nullable=False, server_default='10'),
        sa.Column('y_pct', sa.Float(), nullable=False, server_default='10'),
        sa.Column('w_pct', sa.Float(), nullable=False, server_default='20'),
        sa.Column('h_pct', sa.Float(), nullable=False, server_default='10'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table('event_hotspots')
    op.drop_column('event_pages', 'landing_published')
    op.drop_column('event_pages', 'landing_image_mobile')
    op.drop_column('event_pages', 'landing_image_tablet')
    op.drop_column('event_pages', 'landing_image_desktop')
