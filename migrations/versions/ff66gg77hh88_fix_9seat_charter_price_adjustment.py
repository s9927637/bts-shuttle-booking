"""Fix 九座休旅車 price_adjustment to reflect full charter cost (8 pax × NT$2000 = NT$16000)

Revision ID: ff66gg77hh88
Revises: ee55ff66gg77
Create Date: 2026-10-03

"""
from alembic import op
import sqlalchemy as sa

revision = 'ff66gg77hh88'
down_revision = 'ee55ff66gg77'
branch_labels = None
depends_on = None


def upgrade():
    # 九座休旅車（包車）= 8 人 × NT$2,000 = NT$16,000
    # Base Price（Price Rule）= NT$2,000，price_adjustment = +14,000
    # Final Price = 2,000 + 14,000 = NT$16,000
    op.execute("""
        UPDATE event_vehicle_options
        SET price_adjustment = 14000,
            updated_at = NOW()
        WHERE name = '九座休旅車'
          AND event_id = (SELECT id FROM event_pages WHERE slug = 'vipbooking' LIMIT 1)
    """)


def downgrade():
    op.execute("""
        UPDATE event_vehicle_options
        SET price_adjustment = 0,
            updated_at = NOW()
        WHERE name = '九座休旅車'
          AND event_id = (SELECT id FROM event_pages WHERE slug = 'vipbooking' LIMIT 1)
    """)
