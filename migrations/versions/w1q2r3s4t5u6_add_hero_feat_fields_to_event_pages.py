"""add hero feat fields to event_pages

Revision ID: w1q2r3s4t5u6
Revises: v0p1q2r3s4t5
Create Date: 2026-06-23

"""
from alembic import op
import sqlalchemy as sa

revision = 'w1q2r3s4t5u6'
down_revision = 'v0p1q2r3s4t5'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('event_pages', sa.Column('subtitle',    sa.String(200), nullable=True))
    op.add_column('event_pages', sa.Column('feat1_title', sa.String(60),  nullable=True))
    op.add_column('event_pages', sa.Column('feat1_sub',   sa.String(80),  nullable=True))
    op.add_column('event_pages', sa.Column('feat2_title', sa.String(60),  nullable=True))
    op.add_column('event_pages', sa.Column('feat2_sub',   sa.String(80),  nullable=True))
    op.add_column('event_pages', sa.Column('feat3_title', sa.String(60),  nullable=True))
    op.add_column('event_pages', sa.Column('feat3_sub',   sa.String(80),  nullable=True))
    op.add_column('event_pages', sa.Column('feat4_title', sa.String(60),  nullable=True))
    op.add_column('event_pages', sa.Column('feat4_sub',   sa.String(80),  nullable=True))


def downgrade():
    for col in ['feat4_sub','feat4_title','feat3_sub','feat3_title',
                'feat2_sub','feat2_title','feat1_sub','feat1_title','subtitle']:
        op.drop_column('event_pages', col)
