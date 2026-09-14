"""Seed vipbooking 九座休旅車 vehicle option

Revision ID: a1b2c3d4e5f6
Revises: z4t5u6v7w8x9
Create Date: 2026-09-15

"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = 'z4t5u6v7w8x9'
branch_labels = None
depends_on = None


def upgrade():
    # 將 vipbooking 現有所有車輛方案的 is_default 設為 false
    op.execute("""
        UPDATE event_vehicle_options
        SET is_default = false
        WHERE event_id = (SELECT id FROM event_pages WHERE slug = 'vipbooking' LIMIT 1)
    """)

    # 新增「九座休旅車」（若不存在）排序在最前（sort_order = -1）
    op.execute("""
        INSERT INTO event_vehicle_options
          (event_id, name, capacity, pricing_mode, price_adjustment,
           sort_order, is_default, is_visible, is_active, created_at, updated_at)
        SELECT
          ep.id, '九座休旅車', 6, 'per_person', 0,
          -1, true, true, true, NOW(), NOW()
        FROM event_pages ep
        WHERE ep.slug = 'vipbooking'
          AND NOT EXISTS (
            SELECT 1 FROM event_vehicle_options evo
            WHERE evo.event_id = ep.id AND evo.name = '九座休旅車'
          )
    """)


def downgrade():
    op.execute("""
        DELETE FROM event_vehicle_options
        WHERE name = '九座休旅車'
          AND event_id = (SELECT id FROM event_pages WHERE slug = 'vipbooking' LIMIT 1)
    """)
