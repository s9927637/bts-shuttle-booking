"""Pricing & Payment Refactor — event_pages 新增 pricing_strategy
   （計價模式：passenger 依人數計價 / vehicle 依車輛計價，預設 passenger，
   向下相容既有活動）

Revision ID: q4r5s6t7u8v9
Revises: p3q4r5s6t7u8
Create Date: 2026-07-15
"""
from alembic import op
import sqlalchemy as sa

revision = 'q4r5s6t7u8v9'
down_revision = 'p3q4r5s6t7u8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'event_pages',
        sa.Column('pricing_strategy', sa.String(length=20), nullable=False, server_default='passenger'),
    )


def downgrade():
    op.drop_column('event_pages', 'pricing_strategy')
