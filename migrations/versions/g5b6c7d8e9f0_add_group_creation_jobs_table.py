"""add group_creation_jobs table

Revision ID: g5b6c7d8e9f0
Revises: f4a5b6c7d8e9
Create Date: 2026-06-20
"""
from alembic import op
import sqlalchemy as sa

revision = "g5b6c7d8e9f0"
down_revision = "f4a5b6c7d8e9"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "group_creation_jobs",
        sa.Column("id",              sa.Integer,  primary_key=True),
        sa.Column("concert_id",      sa.Integer,  sa.ForeignKey("concerts.id",      ondelete="SET NULL"), nullable=True,  index=True),
        sa.Column("opportunity_id",  sa.Integer,  sa.ForeignKey("concert_opportunities.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_page_id",   sa.Integer,  sa.ForeignKey("event_pages.id",   ondelete="SET NULL"), nullable=True,  index=True),
        sa.Column("template_id",     sa.Integer,  sa.ForeignKey("event_templates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status",          sa.String(20), nullable=False, server_default="pending"),
        sa.Column("error_message",   sa.Text,     nullable=True),
        sa.Column("created_at",      sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at",      sa.DateTime, server_default=sa.func.now()),
    )
    # indexes already created by SQLAlchemy via index=True on the columns above


def downgrade():
    op.drop_table("group_creation_jobs")
