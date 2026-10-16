"""vipbooking 九座休旅車(共乘) 額滿：前台隱藏，預設改為五座休旅車

Revision ID: ii99jj00kk11
Revises: hh88ii99jj00
Create Date: 2026-10-16

"""
from alembic import op

revision = 'ii99jj00kk11'
down_revision = 'hh88ii99jj00'
branch_labels = None
depends_on = None

_EP = "(SELECT id FROM event_pages WHERE slug = 'vipbooking' LIMIT 1)"


def upgrade():
    # 僅隱藏（不刪除），既有訂單關聯與資料不受影響
    op.execute(f"""
        UPDATE event_vehicle_options
        SET is_visible = false, is_default = false
        WHERE name = '九座休旅車(共乘)' AND event_id = {_EP}
    """)
    op.execute(f"""
        UPDATE event_vehicle_options
        SET is_default = true
        WHERE name = '五座休旅車' AND event_id = {_EP}
    """)


def downgrade():
    pass
