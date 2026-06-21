"""add dispatch_events and dispatch_event_orders tables

Revision ID: p4j5k6l7m8n9
Revises: o3i4j5k6l7m8
Create Date: 2026-06-21

新增多活動排車所需兩張表，不修改既有 dispatches / dispatch_orders。
"""
from alembic import op
import sqlalchemy as sa

revision = 'p4j5k6l7m8n9'
down_revision = 'o3i4j5k6l7m8'
branch_labels = None
depends_on = None


def upgrade():
    # ── dispatch_events ────────────────────────────────────────────────────
    op.create_table(
        'dispatch_events',
        sa.Column('id',              sa.Integer(),     nullable=False),
        sa.Column('event_page_id',   sa.Integer(),     nullable=True),
        sa.Column('dispatch_date',   sa.String(50),    nullable=False),
        sa.Column('departure_city',  sa.String(100),   nullable=True),
        sa.Column('vehicle_count',   sa.Integer(),     nullable=False, server_default='0'),
        sa.Column('passenger_count', sa.Integer(),     nullable=False, server_default='0'),
        sa.Column('status',          sa.String(20),    nullable=False, server_default='規劃中'),
        sa.Column('notes',           sa.Text(),        nullable=True),
        sa.Column('created_at',      sa.DateTime(),    nullable=True),
        sa.Column('updated_at',      sa.DateTime(),    nullable=True),
        sa.ForeignKeyConstraint(['event_page_id'], ['event_pages.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_dispatch_events_event_page_id', 'dispatch_events', ['event_page_id'])
    op.create_index('ix_dispatch_events_dispatch_date',  'dispatch_events', ['dispatch_date'])
    op.create_index('ix_dispatch_events_status',         'dispatch_events', ['status'])

    # ── dispatch_event_orders ──────────────────────────────────────────────
    op.create_table(
        'dispatch_event_orders',
        sa.Column('id',                sa.Integer(), nullable=False),
        sa.Column('dispatch_event_id', sa.Integer(), nullable=False),
        sa.Column('order_id',          sa.Integer(), nullable=False),
        sa.Column('created_at',        sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['dispatch_event_id'], ['dispatch_events.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['order_id'],          ['orders.id'],          ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('dispatch_event_id', 'order_id', name='uq_dispatch_event_order'),
    )
    op.create_index('ix_dispatch_event_orders_dispatch_event_id', 'dispatch_event_orders', ['dispatch_event_id'])
    op.create_index('ix_dispatch_event_orders_order_id',          'dispatch_event_orders', ['order_id'])


def downgrade():
    op.drop_index('ix_dispatch_event_orders_order_id',          table_name='dispatch_event_orders')
    op.drop_index('ix_dispatch_event_orders_dispatch_event_id', table_name='dispatch_event_orders')
    op.drop_table('dispatch_event_orders')

    op.drop_index('ix_dispatch_events_status',         table_name='dispatch_events')
    op.drop_index('ix_dispatch_events_dispatch_date',  table_name='dispatch_events')
    op.drop_index('ix_dispatch_events_event_page_id',  table_name='dispatch_events')
    op.drop_table('dispatch_events')
