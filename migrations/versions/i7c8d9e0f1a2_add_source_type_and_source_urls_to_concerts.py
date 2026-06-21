"""add source_type and source_urls to concerts

Revision ID: i7c8d9e0f1a2
Revises: h6c7d8e9f0a1
Create Date: 2026-06-21
"""
from alembic import op
import sqlalchemy as sa

revision = "i7c8d9e0f1a2"
down_revision = "h6c7d8e9f0a1"
branch_labels = None
depends_on = None


def upgrade():
    # source_type：來源標記，例如 KKTIX / TIXCRAFT / MOCK / MERGED
    op.add_column(
        "concerts",
        sa.Column("source_type", sa.String(50), nullable=True),
    )
    # source_urls：多來源 URL（JSON 字串，跨來源合併時儲存多個連結）
    op.add_column(
        "concerts",
        sa.Column("source_urls", sa.Text, nullable=True),
    )


def downgrade():
    op.drop_column("concerts", "source_urls")
    op.drop_column("concerts", "source_type")
