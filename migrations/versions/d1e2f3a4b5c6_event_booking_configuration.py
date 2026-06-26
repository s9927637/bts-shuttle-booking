"""Event Booking Configuration

Revision ID: d1e2f3a4b5c6
Revises: c9d0e1f2a3b4
Create Date: 2026-06-27

新增：
- event_booking_dates 表（活動可選搭車日期）
- event_pickup_locations 表（活動上車地點）
- event_price_rules 表（日期 + 地點組合定價）
- event_form_configs 表（表單欄位顯示 / 必填設定）
- event_pages: min_group_size, max_group_size, max_capacity, seats_per_vehicle,
               deposit_required, balance_payment_method,
               purchase_notes, cancellation_policy, riding_rules
- orders: pickup_location
"""
from alembic import op
import sqlalchemy as sa

revision = 'd1e2f3a4b5c6'
down_revision = 'c9d0e1f2a3b4'
branch_labels = None
depends_on = None


def upgrade():
    # ── 活動搭車日期 ──────────────────────────────────────────────────────────
    op.create_table(
        'event_booking_dates',
        sa.Column('id',            sa.Integer(),    primary_key=True),
        sa.Column('event_page_id', sa.Integer(),    sa.ForeignKey('event_pages.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('date_value',    sa.String(30),   nullable=False),
        sa.Column('label',         sa.String(100),  nullable=True),
        sa.Column('sort_order',    sa.Integer(),    nullable=False, server_default='0'),
        sa.Column('is_active',     sa.Boolean(),    nullable=False, server_default=sa.text('true')),
        sa.Column('capacity',      sa.Integer(),    nullable=True),
        sa.Column('created_at',    sa.DateTime(),   server_default=sa.text('now()')),
    )

    # ── 活動上車地點 ──────────────────────────────────────────────────────────
    op.create_table(
        'event_pickup_locations',
        sa.Column('id',            sa.Integer(),    primary_key=True),
        sa.Column('event_page_id', sa.Integer(),    sa.ForeignKey('event_pages.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name',          sa.String(100),  nullable=False),
        sa.Column('address',       sa.String(300),  nullable=True),
        sa.Column('map_url',       sa.String(500),  nullable=True),
        sa.Column('sort_order',    sa.Integer(),    nullable=False, server_default='0'),
        sa.Column('is_active',     sa.Boolean(),    nullable=False, server_default=sa.text('true')),
        sa.Column('created_at',    sa.DateTime(),   server_default=sa.text('now()')),
    )

    # ── 活動價格規則 ──────────────────────────────────────────────────────────
    op.create_table(
        'event_price_rules',
        sa.Column('id',              sa.Integer(),  primary_key=True),
        sa.Column('event_page_id',   sa.Integer(),  sa.ForeignKey('event_pages.id',              ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('booking_date_id', sa.Integer(),  sa.ForeignKey('event_booking_dates.id',       ondelete='CASCADE'), nullable=True),
        sa.Column('location_id',     sa.Integer(),  sa.ForeignKey('event_pickup_locations.id',    ondelete='CASCADE'), nullable=True),
        sa.Column('price',           sa.Integer(),  nullable=False),
        sa.Column('deposit',         sa.Integer(),  nullable=False, server_default='0'),
        sa.Column('label',           sa.String(100), nullable=True),
        sa.Column('created_at',      sa.DateTime(), server_default=sa.text('now()')),
    )

    # ── 表單欄位設定 ──────────────────────────────────────────────────────────
    op.create_table(
        'event_form_configs',
        sa.Column('id',             sa.Integer(),   primary_key=True),
        sa.Column('event_page_id',  sa.Integer(),   sa.ForeignKey('event_pages.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('field_name',     sa.String(50),  nullable=False),
        sa.Column('is_visible',     sa.Boolean(),   nullable=False, server_default=sa.text('true')),
        sa.Column('is_required',    sa.Boolean(),   nullable=False, server_default=sa.text('false')),
        sa.Column('label_override', sa.String(100), nullable=True),
        sa.Column('created_at',     sa.DateTime(),  server_default=sa.text('now()')),
        sa.UniqueConstraint('event_page_id', 'field_name', name='uq_event_form_field'),
    )

    # ── EventPage 新欄位 ──────────────────────────────────────────────────────
    op.add_column('event_pages', sa.Column('min_group_size',           sa.Integer(),    nullable=True, server_default='1'))
    op.add_column('event_pages', sa.Column('max_group_size',           sa.Integer(),    nullable=True))
    op.add_column('event_pages', sa.Column('max_capacity',             sa.Integer(),    nullable=True))
    op.add_column('event_pages', sa.Column('seats_per_vehicle',        sa.Integer(),    nullable=True, server_default='9'))
    op.add_column('event_pages', sa.Column('deposit_required',         sa.Boolean(),    nullable=False, server_default=sa.text('true')))
    op.add_column('event_pages', sa.Column('balance_payment_method',   sa.String(50),   nullable=True, server_default='transfer'))
    op.add_column('event_pages', sa.Column('purchase_notes',           sa.Text(),       nullable=True))
    op.add_column('event_pages', sa.Column('cancellation_policy',      sa.Text(),       nullable=True))
    op.add_column('event_pages', sa.Column('riding_rules',             sa.Text(),       nullable=True))

    # ── Order 新欄位 ──────────────────────────────────────────────────────────
    op.add_column('orders', sa.Column('pickup_location', sa.String(100), nullable=True))


def downgrade():
    op.drop_column('orders', 'pickup_location')

    op.drop_column('event_pages', 'riding_rules')
    op.drop_column('event_pages', 'cancellation_policy')
    op.drop_column('event_pages', 'purchase_notes')
    op.drop_column('event_pages', 'balance_payment_method')
    op.drop_column('event_pages', 'deposit_required')
    op.drop_column('event_pages', 'seats_per_vehicle')
    op.drop_column('event_pages', 'max_capacity')
    op.drop_column('event_pages', 'max_group_size')
    op.drop_column('event_pages', 'min_group_size')

    op.drop_table('event_form_configs')
    op.drop_table('event_price_rules')
    op.drop_table('event_pickup_locations')
    op.drop_table('event_booking_dates')
