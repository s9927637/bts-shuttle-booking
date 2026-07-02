"""Phase 3: Landing Page Builder — event_sections 響應式顯示 + 主題欄位

Revision ID: g4h5i6j7k8l9
Revises: f3a4b5c6d7e8
Create Date: 2026-07-02
"""
from alembic import op
import sqlalchemy as sa

revision = 'g4h5i6j7k8l9'
down_revision = 'f3a4b5c6d7e8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('event_sections', sa.Column('show_desktop', sa.Boolean(), nullable=True))
    op.add_column('event_sections', sa.Column('show_tablet', sa.Boolean(), nullable=True))
    op.add_column('event_sections', sa.Column('show_mobile', sa.Boolean(), nullable=True))
    op.add_column('event_sections', sa.Column('theme_style', sa.String(length=20), nullable=True))


def downgrade():
    op.drop_column('event_sections', 'theme_style')
    op.drop_column('event_sections', 'show_mobile')
    op.drop_column('event_sections', 'show_tablet')
    op.drop_column('event_sections', 'show_desktop')
