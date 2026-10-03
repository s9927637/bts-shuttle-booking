"""vipbooking 上車地點固定為台北車站（下拉選單）

Revision ID: gg77hh88ii99
Revises: ff66gg77hh88
Create Date: 2026-10-03

"""
from alembic import op

revision = 'gg77hh88ii99'
down_revision = 'ff66gg77hh88'
branch_labels = None
depends_on = None

_EP = "(SELECT id FROM event_pages WHERE slug = 'vipbooking' LIMIT 1)"


def upgrade():
    # 1) 既有「自訂輸入」地點轉為固定台北車站（保留 id，價格規則關聯不變）
    op.execute(f"""
        UPDATE event_pickup_locations
        SET name = '台北車站', is_custom_location = false, is_active = true
        WHERE id = (
            SELECT id FROM event_pickup_locations
            WHERE event_page_id = {_EP} AND is_custom_location = true
            ORDER BY sort_order, id LIMIT 1
        )
    """)
    # 2) 若活動尚無「台北車站」地點則新增
    op.execute(f"""
        INSERT INTO event_pickup_locations
            (event_page_id, name, sort_order, is_active, is_custom_location, created_at)
        SELECT {_EP}, '台北車站', 0, true, false, NOW()
        WHERE {_EP} IS NOT NULL
          AND NOT EXISTS (
            SELECT 1 FROM event_pickup_locations
            WHERE event_page_id = {_EP} AND name = '台北車站'
          )
    """)
    # 3) 其餘地點停用（不刪除，舊訂單存的是名稱快照）
    op.execute(f"""
        UPDATE event_pickup_locations
        SET is_active = false
        WHERE event_page_id = {_EP} AND name <> '台北車站'
    """)


def downgrade():
    pass
