"""add concert_data_hub table

Revision ID: j8d9e0f1a2b3
Revises: i7c8d9e0f1a2
Create Date: 2026-06-21
"""
from alembic import op
import sqlalchemy as sa

revision = "j8d9e0f1a2b3"
down_revision = "i7c8d9e0f1a2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "concert_data_hub",
        sa.Column("id",               sa.Integer,     primary_key=True),
        sa.Column("concert_id",       sa.Integer,     sa.ForeignKey("concerts.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("artist_name",      sa.String(100), nullable=False),
        sa.Column("concert_name",     sa.String(200), nullable=False),
        sa.Column("event_date",       sa.Date,        nullable=True),
        sa.Column("venue",            sa.String(200), nullable=True),
        sa.Column("city",             sa.String(50),  nullable=True),
        sa.Column("ticket_sale_date", sa.String(100), nullable=True),
        sa.Column("source_count",     sa.Integer,     nullable=False, default=0),
        sa.Column("source_types",     sa.String(100), nullable=True),
        sa.Column("source_urls",      sa.Text,        nullable=True),
        sa.Column("confidence_score", sa.Integer,     nullable=False, default=0),
        sa.Column("status",           sa.String(20),  nullable=False, default="active"),
        sa.Column("has_conflict",     sa.Boolean,     nullable=False, default=False),
        sa.Column("conflict_types",   sa.String(200), nullable=True),
        sa.Column("created_at",       sa.DateTime,    nullable=True),
        sa.Column("updated_at",       sa.DateTime,    nullable=True),
    )


def downgrade():
    op.drop_table("concert_data_hub")
