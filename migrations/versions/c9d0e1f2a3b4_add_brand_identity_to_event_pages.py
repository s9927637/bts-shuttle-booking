"""Add brand identity fields to event_pages

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-06-27

"""
from alembic import op
import sqlalchemy as sa

revision = 'c9d0e1f2a3b4'
down_revision = 'b8c9d0e1f2a3'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('event_pages', sa.Column('logo_image', sa.String(500), nullable=True))
    op.add_column('event_pages', sa.Column('logo_text',  sa.String(100), nullable=True))
    op.add_column('event_pages', sa.Column('logo_link',  sa.String(200), nullable=True))


def downgrade():
    op.drop_column('event_pages', 'logo_link')
    op.drop_column('event_pages', 'logo_text')
    op.drop_column('event_pages', 'logo_image')
