"""Phase 4: Landing Page 自由編輯（唯一可自訂 HTML 的頁面）

Revision ID: h5i6j7k8l9m0
Revises: g4h5i6j7k8l9
Create Date: 2026-07-02
"""
from alembic import op
import sqlalchemy as sa

revision = 'h5i6j7k8l9m0'
down_revision = 'g4h5i6j7k8l9'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('event_pages', sa.Column('landing_html', sa.Text(), nullable=True))
    op.add_column('event_pages', sa.Column('landing_css', sa.Text(), nullable=True))
    op.add_column('event_pages', sa.Column('landing_js', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('event_pages', 'landing_js')
    op.drop_column('event_pages', 'landing_css')
    op.drop_column('event_pages', 'landing_html')
