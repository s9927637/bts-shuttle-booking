"""上車地點支援「乘客自行輸入」— event_pickup_locations 新增 is_custom_location，
   orders 新增 pickup_location_text 快照欄位

Revision ID: o2p3q4r5s6t7
Revises: n1o2p3q4r5s6
Create Date: 2026-07-14
"""
from alembic import op
import sqlalchemy as sa

revision = 'o2p3q4r5s6t7'
down_revision = 'n1o2p3q4r5s6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'event_pickup_locations',
        sa.Column('is_custom_location', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        'orders',
        sa.Column('pickup_location_text', sa.String(length=200), nullable=True),
    )


def downgrade():
    op.drop_column('orders', 'pickup_location_text')
    op.drop_column('event_pickup_locations', 'is_custom_location')
