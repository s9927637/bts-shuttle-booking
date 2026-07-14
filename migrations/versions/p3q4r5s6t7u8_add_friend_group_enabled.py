"""Feature：Booking Settings Enhancement — event_pages 新增 friend_group_enabled
   （朋友同行功能開關，預設 true，向下相容既有活動）

Revision ID: p3q4r5s6t7u8
Revises: o2p3q4r5s6t7
Create Date: 2026-07-15
"""
from alembic import op
import sqlalchemy as sa

revision = 'p3q4r5s6t7u8'
down_revision = 'o2p3q4r5s6t7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'event_pages',
        sa.Column('friend_group_enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade():
    op.drop_column('event_pages', 'friend_group_enabled')
