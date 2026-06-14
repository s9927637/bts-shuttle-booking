"""fix announcements missing columns — idempotent ADD COLUMN IF NOT EXISTS

f7f9ced00dd5 加入 NOT NULL 欄位時缺少 server_default，
在有既有資料的 PostgreSQL 上會靜默失敗導致欄位未建立。
本 migration 用 ADD COLUMN IF NOT EXISTS 補齊所有缺失欄位，
並加上 server_default，完全冪等（重複執行不影響資料）。

Revision ID: d1306f6cc087
Revises: 7c07dc5449e1
Create Date: 2026-06-14
"""
from alembic import op

revision = 'd1306f6cc087'
down_revision = '7c07dc5449e1'
branch_labels = None
depends_on = None


def upgrade():
    # 使用原生 SQL ADD COLUMN IF NOT EXISTS，確保冪等性
    op.execute("""
        ALTER TABLE announcements
            ADD COLUMN IF NOT EXISTS announcement_type VARCHAR(20) NOT NULL DEFAULT '一般公告',
            ADD COLUMN IF NOT EXISTS status            VARCHAR(20) NOT NULL DEFAULT '草稿',
            ADD COLUMN IF NOT EXISTS is_pinned         BOOLEAN     NOT NULL DEFAULT false,
            ADD COLUMN IF NOT EXISTS publish_to_line   BOOLEAN     NOT NULL DEFAULT false,
            ADD COLUMN IF NOT EXISTS line_target       VARCHAR(50),
            ADD COLUMN IF NOT EXISTS updated_at        TIMESTAMP
    """)


def downgrade():
    # downgrade 刻意為空：這些欄位在 f7f9ced00dd5 中已定義為可降級，
    # 此處不重複刪除以避免與前一個 migration 衝突。
    pass
