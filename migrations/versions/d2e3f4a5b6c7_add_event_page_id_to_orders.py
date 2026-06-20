"""add event_page_id to orders

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-06-20

向 orders 新增 event_page_id（可為 NULL），外鍵指向 event_pages.id。
既有 BTS 訂單 event_page_id = NULL，完全不受影響。
"""
from alembic import op
import sqlalchemy as sa

revision = 'd2e3f4a5b6c7'
down_revision = 'c1d2e3f4a5b6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('orders', sa.Column('event_page_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_orders_event_page_id',
        'orders', 'event_pages',
        ['event_page_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_index('ix_orders_event_page_id', 'orders', ['event_page_id'])


def downgrade():
    op.drop_index('ix_orders_event_page_id', table_name='orders')
    op.drop_constraint('fk_orders_event_page_id', 'orders', type_='foreignkey')
    op.drop_column('orders', 'event_page_id')
