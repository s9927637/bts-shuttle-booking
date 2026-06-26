"""Add custom_css to event_pages

Revision ID: b8c9d0e1f2a3
Revises: a5u6v7w8x9y0
Create Date: 2026-06-26

"""
from alembic import op
import sqlalchemy as sa

revision = 'b8c9d0e1f2a3'
down_revision = 'a5u6v7w8x9y0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('event_pages', sa.Column('custom_css', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('event_pages', 'custom_css')
