"""Feature：Vehicle Options（車輛方案 V2）— 新增 event_vehicle_options 資料表，
   orders 新增快照欄位（vehicle_option_id/name/capacity/pricing_mode）

Revision ID: n1o2p3q4r5s6
Revises: m0n1o2p3q4r5
Create Date: 2026-07-14
"""
from alembic import op
import sqlalchemy as sa

revision = 'n1o2p3q4r5s6'
down_revision = 'm0n1o2p3q4r5'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'event_vehicle_options',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('event_id', sa.Integer(), sa.ForeignKey('event_pages.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('example_models', sa.String(length=500), nullable=True),
        sa.Column('capacity', sa.Integer(), nullable=False, server_default='4'),
        sa.Column('image', sa.String(length=500), nullable=True),
        sa.Column('pricing_mode', sa.String(length=20), nullable=False, server_default='event_price'),
        sa.Column('price', sa.Integer(), nullable=True),
        sa.Column('price_adjustment', sa.Integer(), nullable=True),
        sa.Column('badge', sa.String(length=50), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('is_visible', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_event_vehicle_options_event_id', 'event_vehicle_options', ['event_id'])

    # orders：新增快照欄位，避免日後修改／刪除方案影響歷史訂單顯示
    op.add_column('orders', sa.Column('vehicle_option_id', sa.Integer(),
                   sa.ForeignKey('event_vehicle_options.id', ondelete='SET NULL'), nullable=True))
    op.add_column('orders', sa.Column('vehicle_option_name', sa.String(length=100), nullable=True))
    op.add_column('orders', sa.Column('vehicle_option_capacity', sa.Integer(), nullable=True))
    op.add_column('orders', sa.Column('vehicle_option_pricing_mode', sa.String(length=20), nullable=True))


def downgrade():
    op.drop_column('orders', 'vehicle_option_pricing_mode')
    op.drop_column('orders', 'vehicle_option_capacity')
    op.drop_column('orders', 'vehicle_option_name')
    op.drop_column('orders', 'vehicle_option_id')
    op.drop_index('ix_event_vehicle_options_event_id', table_name='event_vehicle_options')
    op.drop_table('event_vehicle_options')
