"""Add hero_image_desktop / tablet / mobile to event_pages

Revision ID: z4t5u6v7w8x9
Revises: y3s4t5u6v7w8
Create Date: 2026-06-24

"""
from alembic import op
import sqlalchemy as sa

revision = 'z4t5u6v7w8x9'
down_revision = 'y3s4t5u6v7w8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('event_pages', sa.Column('hero_image_desktop', sa.String(500), nullable=True))
    op.add_column('event_pages', sa.Column('hero_image_tablet',  sa.String(500), nullable=True))
    op.add_column('event_pages', sa.Column('hero_image_mobile',  sa.String(500), nullable=True))


def downgrade():
    op.drop_column('event_pages', 'hero_image_mobile')
    op.drop_column('event_pages', 'hero_image_tablet')
    op.drop_column('event_pages', 'hero_image_desktop')
