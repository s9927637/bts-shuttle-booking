"""品牌設定優化：Logo Display Mode（System Logo ｜ Landing Logo Hotspot）

Revision ID: l9m0n1o2p3q4
Revises: k8l9m0n1o2p3
Create Date: 2026-07-09
"""
from alembic import op
import sqlalchemy as sa

revision = 'l9m0n1o2p3q4'
down_revision = 'k8l9m0n1o2p3'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('event_pages', sa.Column('logo_display_mode', sa.String(length=20), nullable=True))
    op.add_column('event_pages', sa.Column('logo_hotspot_desktop_x', sa.Float(), nullable=True))
    op.add_column('event_pages', sa.Column('logo_hotspot_desktop_y', sa.Float(), nullable=True))
    op.add_column('event_pages', sa.Column('logo_hotspot_desktop_w', sa.Float(), nullable=True))
    op.add_column('event_pages', sa.Column('logo_hotspot_desktop_h', sa.Float(), nullable=True))
    op.add_column('event_pages', sa.Column('logo_hotspot_tablet_x', sa.Float(), nullable=True))
    op.add_column('event_pages', sa.Column('logo_hotspot_tablet_y', sa.Float(), nullable=True))
    op.add_column('event_pages', sa.Column('logo_hotspot_tablet_w', sa.Float(), nullable=True))
    op.add_column('event_pages', sa.Column('logo_hotspot_tablet_h', sa.Float(), nullable=True))
    op.add_column('event_pages', sa.Column('logo_hotspot_mobile_x', sa.Float(), nullable=True))
    op.add_column('event_pages', sa.Column('logo_hotspot_mobile_y', sa.Float(), nullable=True))
    op.add_column('event_pages', sa.Column('logo_hotspot_mobile_w', sa.Float(), nullable=True))
    op.add_column('event_pages', sa.Column('logo_hotspot_mobile_h', sa.Float(), nullable=True))


def downgrade():
    op.drop_column('event_pages', 'logo_hotspot_mobile_h')
    op.drop_column('event_pages', 'logo_hotspot_mobile_w')
    op.drop_column('event_pages', 'logo_hotspot_mobile_y')
    op.drop_column('event_pages', 'logo_hotspot_mobile_x')
    op.drop_column('event_pages', 'logo_hotspot_tablet_h')
    op.drop_column('event_pages', 'logo_hotspot_tablet_w')
    op.drop_column('event_pages', 'logo_hotspot_tablet_y')
    op.drop_column('event_pages', 'logo_hotspot_tablet_x')
    op.drop_column('event_pages', 'logo_hotspot_desktop_h')
    op.drop_column('event_pages', 'logo_hotspot_desktop_w')
    op.drop_column('event_pages', 'logo_hotspot_desktop_y')
    op.drop_column('event_pages', 'logo_hotspot_desktop_x')
    op.drop_column('event_pages', 'logo_display_mode')
