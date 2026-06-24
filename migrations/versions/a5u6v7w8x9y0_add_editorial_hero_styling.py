"""add editorial hero styling fields

Revision ID: a5u6v7w8x9y0
Revises: z4t5u6v7w8x9
Create Date: 2026-06-24
"""
from alembic import op
import sqlalchemy as sa

revision = 'a5u6v7w8x9y0'
down_revision = 'z4t5u6v7w8x9'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('event_pages', sa.Column('hero_title_color',    sa.String(20), nullable=True))
    op.add_column('event_pages', sa.Column('hero_subtitle_color', sa.String(20), nullable=True))
    op.add_column('event_pages', sa.Column('hero_text_color',     sa.String(20), nullable=True))
    op.add_column('event_pages', sa.Column('hero_btn_color',      sa.String(20), nullable=True))
    op.add_column('event_pages', sa.Column('hero_overlay',        sa.String(20), nullable=True))
    op.add_column('event_pages', sa.Column('hero_title_size',     sa.String(10), nullable=True))


def downgrade():
    op.drop_column('event_pages', 'hero_title_size')
    op.drop_column('event_pages', 'hero_overlay')
    op.drop_column('event_pages', 'hero_btn_color')
    op.drop_column('event_pages', 'hero_text_color')
    op.drop_column('event_pages', 'hero_subtitle_color')
    op.drop_column('event_pages', 'hero_title_color')
