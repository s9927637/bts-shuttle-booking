"""Deposit Type Enhancement — event_pages 新增 deposit_type / deposit_percentage

訂金計算改為完全由事件層級的「訂金方式」決定，取代原本逐條 Price Rule
自訂訂金金額的設計（EventPriceRule.deposit 欄位保留不刪除，僅停用）：
- deposit_type='fixed'（預設，向下相容）：沿用既有 EventPage.deposit
  作為固定金額（依人數計價時 ×人數，依車輛計價時為單一金額）
- deposit_type='percentage'：訂金 = 總價 × deposit_percentage%

Revision ID: s6t7u8v9w0x1
Revises: r5s6t7u8v9w0
Create Date: 2026-07-15
"""
from alembic import op
import sqlalchemy as sa

revision = 's6t7u8v9w0x1'
down_revision = 'r5s6t7u8v9w0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'event_pages',
        sa.Column('deposit_type', sa.String(length=20), nullable=False, server_default='fixed'),
    )
    op.add_column(
        'event_pages',
        sa.Column('deposit_percentage', sa.Integer(), nullable=False, server_default='30'),
    )


def downgrade():
    op.drop_column('event_pages', 'deposit_percentage')
    op.drop_column('event_pages', 'deposit_type')
