"""Revert bb22cc33dd44 and insert brand-new 九座休旅車(容量6) for vipbooking

Revision ID: cc33dd44ee55
Revises: bb22cc33dd44
Create Date: 2026-09-15

"""
from alembic import op
import sqlalchemy as sa

revision = 'cc33dd44ee55'
down_revision = 'bb22cc33dd44'
branch_labels = None
depends_on = None


def upgrade():
    # 1. 把 bb22cc33dd44 錯誤更新的九座休旅車還原回原始狀態（容量8、一般計價、非預設）
    op.execute("""
        UPDATE event_vehicle_options
        SET capacity      = 8,
            pricing_mode  = 'event_price',
            sort_order    = 0,
            is_default    = false,
            updated_at    = NOW()
        WHERE name = '九座休旅車'
          AND event_id = (SELECT id FROM event_pages WHERE slug = 'vipbooking' LIMIT 1)
    """)

    # 2. 把所有方案的 is_default 設為 false
    op.execute("""
        UPDATE event_vehicle_options
        SET is_default = false
        WHERE event_id = (SELECT id FROM event_pages WHERE slug = 'vipbooking' LIMIT 1)
    """)

    # 3. 新增全新的「九座休旅車」方案（容量6、依人數計費、排序第一、預設選中）
    op.execute("""
        INSERT INTO event_vehicle_options
          (event_id, name, capacity, pricing_mode, price_adjustment,
           sort_order, is_default, is_visible, is_active, created_at, updated_at)
        SELECT
          ep.id, '九座休旅車(共乘)', 6, 'per_person', 0,
          -1, true, true, true, NOW(), NOW()
        FROM event_pages ep
        WHERE ep.slug = 'vipbooking'
          AND NOT EXISTS (
            SELECT 1 FROM event_vehicle_options evo
            WHERE evo.event_id = ep.id AND evo.name = '九座休旅車(共乘)'
          )
    """)


def downgrade():
    op.execute("""
        DELETE FROM event_vehicle_options
        WHERE name = '九座休旅車(共乘)'
          AND event_id = (SELECT id FROM event_pages WHERE slug = 'vipbooking' LIMIT 1)
    """)
    op.execute("""
        UPDATE event_vehicle_options
        SET capacity     = 6,
            pricing_mode = 'per_person',
            sort_order   = -1,
            is_default   = true,
            updated_at   = NOW()
        WHERE name = '九座休旅車'
          AND event_id = (SELECT id FROM event_pages WHERE slug = 'vipbooking' LIMIT 1)
    """)
