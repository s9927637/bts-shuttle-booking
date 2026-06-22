"""add hero_variant and tour_name to event_pages

Revision ID: x2r3s4t5u6v7
Revises: w1q2r3s4t5u6
Create Date: 2026-06-23

"""
from alembic import op
import sqlalchemy as sa

revision = 'x2r3s4t5u6v7'
down_revision = 'w1q2r3s4t5u6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('event_pages', sa.Column('hero_variant', sa.String(30),  nullable=True))
    op.add_column('event_pages', sa.Column('tour_name',    sa.String(200), nullable=True))


def downgrade():
    op.drop_column('event_pages', 'tour_name')
    op.drop_column('event_pages', 'hero_variant')
