"""Vehicle Option Pricing 簡化版 — price_adjustment 補預設值 0 並回填既有 NULL

不刪除 pricing_mode / price 欄位（仍保留供歷史資料與未來評估使用，
本次僅停止在新計價邏輯中讀取它們，詳見 PR 說明的 Migration 建議）。

Revision ID: r5s6t7u8v9w0
Revises: q4r5s6t7u8v9
Create Date: 2026-07-15
"""
from alembic import op
import sqlalchemy as sa

revision = 'r5s6t7u8v9w0'
down_revision = 'q4r5s6t7u8v9'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE event_vehicle_options SET price_adjustment = 0 WHERE price_adjustment IS NULL")
    op.alter_column(
        'event_vehicle_options', 'price_adjustment',
        existing_type=sa.Integer(),
        nullable=False,
        server_default='0',
    )


def downgrade():
    op.alter_column(
        'event_vehicle_options', 'price_adjustment',
        existing_type=sa.Integer(),
        nullable=True,
        server_default=None,
    )
