"""Fix 九座休旅車(共乘) capacity from 6 to 8 for vipbooking

Revision ID: dd44ee55ff66
Revises: cc33dd44ee55
Create Date: 2026-09-15

"""
from alembic import op
import sqlalchemy as sa

revision = 'dd44ee55ff66'
down_revision = 'cc33dd44ee55'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        UPDATE event_vehicle_options
        SET capacity   = 8,
            updated_at = NOW()
        WHERE name = '九座休旅車(共乘)'
          AND event_id = (SELECT id FROM event_pages WHERE slug = 'vipbooking' LIMIT 1)
    """)


def downgrade():
    op.execute("""
        UPDATE event_vehicle_options
        SET capacity   = 6,
            updated_at = NOW()
        WHERE name = '九座休旅車(共乘)'
          AND event_id = (SELECT id FROM event_pages WHERE slug = 'vipbooking' LIMIT 1)
    """)
