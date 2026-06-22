"""add theme_color to event_pages and migrate BTS orders

Revision ID: t8n9o0p1q2r3
Revises: s7m8n9o0p1q2
Create Date: 2026-06-22

安全性說明：
- 不刪除任何訂單、付款、收據資料
- 只新增 theme_color 欄位
- Data migration：找到/建立 BTS event_page，將既有 BTS 訂單（event_page_id IS NULL）關聯至 BTS event_page
- Rollback 時設回 NULL（不刪除建立的 BTS event_page）
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = 't8n9o0p1q2r3'
down_revision = 's7m8n9o0p1q2'
branch_labels = None
depends_on = None


def upgrade():
    # ── 1. 新增 theme_color 欄位 ──────────────────────────────────────────────
    op.add_column('event_pages', sa.Column('theme_color', sa.String(30), nullable=True, server_default='purple'))

    # ── 2. 既有 BTS 訂單遷移 ─────────────────────────────────────────────────
    bind = op.get_bind()

    # 先確認有無未關聯訂單（event_page_id IS NULL）
    null_cnt = bind.execute(text("SELECT COUNT(*) FROM orders WHERE event_page_id IS NULL")).scalar()
    if null_cnt == 0:
        return   # 無需遷移

    # 找現有 BTS event_page（artist_name='BTS'，優先取最舊的）
    row = bind.execute(
        text("SELECT id FROM event_pages WHERE artist_name = 'BTS' AND deleted_at IS NULL ORDER BY id ASC LIMIT 1")
    ).fetchone()

    if row:
        bts_id = row[0]
    else:
        # 建立 BTS event_page（歷史訂單用，不影響既有頁面）
        # slug 用 bts-kaohsiung-legacy 避免與現有 bts-kaohsiung 衝突
        slug = 'bts-kaohsiung-legacy'
        existing_slug = bind.execute(
            text("SELECT id FROM event_pages WHERE slug = :slug"), {'slug': slug}
        ).fetchone()
        if existing_slug:
            # slug 已存在，表示此 event_page 已存在，直接用它
            bts_id = existing_slug[0]
        else:
            bind.execute(text("""
                INSERT INTO event_pages (title, slug, artist_name, event_name, status, category, theme_color, created_at, updated_at)
                VALUES ('BTS 高雄演唱會包車', :slug, 'BTS', 'BTS WORLD TOUR MAP OF THE SOUL — SEOUL', '已發布', 'concert', 'purple', NOW(), NOW())
            """), {'slug': slug})
            bts_id = bind.execute(
                text("SELECT id FROM event_pages WHERE slug = :slug"), {'slug': slug}
            ).fetchone()[0]

    # 將所有 event_page_id IS NULL 的訂單關聯至 BTS
    updated = bind.execute(
        text("UPDATE orders SET event_page_id = :bts_id WHERE event_page_id IS NULL"),
        {'bts_id': bts_id}
    ).rowcount

    print(f"\n[Migration t8n9o0p1q2r3] BTS event_page id={bts_id}，已遷移 {updated} 筆既有訂單。\n")


def downgrade():
    # 回滾：將透過本次 migration 建立 event_page 的訂單設回 NULL
    # 注意：無法精確知道哪些是本次遷移的，因此保守做法是移除 theme_color 欄位
    # 訂單的 event_page_id 不回滾（保留關聯，避免資料遺失）
    op.drop_column('event_pages', 'theme_color')
