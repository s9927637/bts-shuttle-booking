"""add order_events table

Revision ID: o3i4j5k6l7m8
Revises: n2h3i4j5k6l7
Create Date: 2026-06-21

新增 order_events mapping table：
  - 不修改 orders 資料表結構
  - BTS 舊訂單不建立任何 mapping，完全不受影響
"""
from alembic import op
import sqlalchemy as sa

revision = 'o3i4j5k6l7m8'
down_revision = 'n2h3i4j5k6l7'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'order_events',
        sa.Column('id',            sa.Integer(),  nullable=False),
        sa.Column('order_id',      sa.Integer(),  nullable=False),
        sa.Column('event_page_id', sa.Integer(),  nullable=False),
        sa.Column('created_at',    sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['order_id'],      ['orders.id'],      ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['event_page_id'], ['event_pages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('order_id', 'event_page_id', name='uq_order_event'),
    )
    op.create_index('ix_order_events_order_id',      'order_events', ['order_id'])
    op.create_index('ix_order_events_event_page_id', 'order_events', ['event_page_id'])


def downgrade():
    op.drop_index('ix_order_events_event_page_id', table_name='order_events')
    op.drop_index('ix_order_events_order_id',      table_name='order_events')
    op.drop_table('order_events')
