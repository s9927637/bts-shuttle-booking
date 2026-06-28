"""Event Theme System

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-06-28

新增：
- event_pages: theme_primary_color, theme_secondary_color, theme_bg_color,
               theme_text_color, theme_btn_color, theme_btn_text_color, theme_navbar
"""
from alembic import op
import sqlalchemy as sa

revision = 'e2f3a4b5c6d7'
down_revision = 'd1e2f3a4b5c6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('event_pages', sa.Column('theme_primary_color',   sa.String(20), nullable=True))
    op.add_column('event_pages', sa.Column('theme_secondary_color', sa.String(20), nullable=True))
    op.add_column('event_pages', sa.Column('theme_bg_color',        sa.String(20), nullable=True))
    op.add_column('event_pages', sa.Column('theme_text_color',      sa.String(20), nullable=True))
    op.add_column('event_pages', sa.Column('theme_btn_color',       sa.String(20), nullable=True))
    op.add_column('event_pages', sa.Column('theme_btn_text_color',  sa.String(20), nullable=True))
    op.add_column('event_pages', sa.Column('theme_navbar',          sa.String(10), nullable=True, server_default='auto'))


def downgrade():
    op.drop_column('event_pages', 'theme_navbar')
    op.drop_column('event_pages', 'theme_btn_text_color')
    op.drop_column('event_pages', 'theme_btn_color')
    op.drop_column('event_pages', 'theme_text_color')
    op.drop_column('event_pages', 'theme_bg_color')
    op.drop_column('event_pages', 'theme_secondary_color')
    op.drop_column('event_pages', 'theme_primary_color')
