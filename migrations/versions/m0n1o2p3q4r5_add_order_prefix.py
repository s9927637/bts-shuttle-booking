"""Bug Fix：每個活動獨立 Order Number Prefix（event_pages.order_prefix）

Revision ID: m0n1o2p3q4r5
Revises: l9m0n1o2p3q4
Create Date: 2026-07-10
"""
from alembic import op
import sqlalchemy as sa

revision = 'm0n1o2p3q4r5'
down_revision = 'l9m0n1o2p3q4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('event_pages', sa.Column('order_prefix', sa.String(length=20), nullable=True))


def downgrade():
    op.drop_column('event_pages', 'order_prefix')
