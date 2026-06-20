"""add source_url to concerts

Revision ID: h6c7d8e9f0a1
Revises: g5b6c7d8e9f0
Create Date: 2026-06-20
"""
from alembic import op
import sqlalchemy as sa

revision = "h6c7d8e9f0a1"
down_revision = "g5b6c7d8e9f0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("concerts", sa.Column("source_url", sa.String(500), nullable=True))


def downgrade():
    op.drop_column("concerts", "source_url")
