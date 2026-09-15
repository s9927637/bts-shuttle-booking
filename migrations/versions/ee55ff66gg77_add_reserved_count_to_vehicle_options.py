"""Add reserved_count to event_vehicle_options; set 2 for vipbooking 九座休旅車(共乘)

Revision ID: ee55ff66gg77
Revises: dd44ee55ff66
Create Date: 2026-09-15

"""
from alembic import op
import sqlalchemy as sa

revision = 'ee55ff66gg77'
down_revision = 'dd44ee55ff66'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'event_vehicle_options',
        sa.Column('reserved_count', sa.Integer(), nullable=False, server_default='0')
    )
    op.execute("""
        UPDATE event_vehicle_options
        SET reserved_count = 2
        WHERE name = '九座休旅車(共乘)'
          AND event_id = (SELECT id FROM event_pages WHERE slug = 'vipbooking' LIMIT 1)
    """)


def downgrade():
    op.drop_column('event_vehicle_options', 'reserved_count')
