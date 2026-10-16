"""vipbooking 五座休旅車 3500/人，整車 NT$14,000（基礎 2000 + 調整 12000）

Revision ID: jj00kk11ll22
Revises: ii99jj00kk11
Create Date: 2026-10-16

"""
from alembic import op

revision = 'jj00kk11ll22'
down_revision = 'ii99jj00kk11'
branch_labels = None
depends_on = None


def upgrade():
    # 僅調整方案價格差額；既有訂單的金額為建立時快照，不受影響
    op.execute("""
        UPDATE event_vehicle_options
        SET price_adjustment = 12000
        WHERE name = '五座休旅車'
          AND event_id = (SELECT id FROM event_pages WHERE slug = 'vipbooking' LIMIT 1)
    """)


def downgrade():
    pass
