"""Fix vipbooking 九座休旅車 specs (capacity=6, sort_order=-1, is_default, per_person)

Revision ID: bb22cc33dd44
Revises: aa11bb22cc33
Create Date: 2026-09-15

"""
from alembic import op
import sqlalchemy as sa

revision = 'bb22cc33dd44'
down_revision = 'aa11bb22cc33'
branch_labels = None
depends_on = None


def upgrade():
    # 先把 vipbooking 其他方案的 is_default 設為 false
    op.execute("""
        UPDATE event_vehicle_options
        SET is_default = false
        WHERE event_id = (SELECT id FROM event_pages WHERE slug = 'vipbooking' LIMIT 1)
    """)

    # 更新「九座休旅車」為正確規格（不管原本 capacity 是多少）
    op.execute("""
        UPDATE event_vehicle_options
        SET capacity      = 6,
            pricing_mode  = 'per_person',
            price_adjustment = 0,
            sort_order    = -1,
            is_default    = true,
            is_visible    = true,
            is_active     = true,
            updated_at    = NOW()
        WHERE name = '九座休旅車'
          AND event_id = (SELECT id FROM event_pages WHERE slug = 'vipbooking' LIMIT 1)
    """)


def downgrade():
    # 回到 capacity=8（原始值），移除 per_person 模式
    op.execute("""
        UPDATE event_vehicle_options
        SET capacity      = 8,
            pricing_mode  = NULL,
            sort_order    = 0,
            is_default    = false,
            updated_at    = NOW()
        WHERE name = '九座休旅車'
          AND event_id = (SELECT id FROM event_pages WHERE slug = 'vipbooking' LIMIT 1)
    """)
