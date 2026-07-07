"""Bug Fix Phase 1: Hotspot 依裝置分離（Desktop/Tablet/Mobile 各自獨立）

Revision ID: k8l9m0n1o2p3
Revises: j7k8l9m0n1o2
Create Date: 2026-07-08
"""
from alembic import op
import sqlalchemy as sa

revision = 'k8l9m0n1o2p3'
down_revision = 'j7k8l9m0n1o2'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('event_hotspots', sa.Column('device', sa.String(length=10), nullable=False, server_default='desktop'))


def downgrade():
    op.drop_column('event_hotspots', 'device')
