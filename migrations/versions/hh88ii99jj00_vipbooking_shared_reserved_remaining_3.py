"""vipbooking 九座休旅車(共乘) 預留席位調整，使目前剩餘位置為 3

Revision ID: hh88ii99jj00
Revises: gg77hh88ii99
Create Date: 2026-10-07

"""
from alembic import op

revision = 'hh88ii99jj00'
down_revision = 'gg77hh88ii99'
branch_labels = None
depends_on = None


def upgrade():
    # reserved_count = capacity - 目標剩餘(3) - 現有未取消訂單人數；只改預留數，不動任何訂單
    op.execute("""
        UPDATE event_vehicle_options vo
        SET reserved_count = GREATEST(0, vo.capacity - 3 - COALESCE((
            SELECT SUM(o.passenger_count) FROM orders o
            WHERE o.vehicle_option_id = vo.id AND o.payment_status <> '已取消'
        ), 0))
        WHERE vo.name = '九座休旅車(共乘)'
          AND vo.event_id = (SELECT id FROM event_pages WHERE slug = 'vipbooking' LIMIT 1)
    """)


def downgrade():
    pass
