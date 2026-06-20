"""add event_templates table

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-06-20
"""
from alembic import op
import sqlalchemy as sa

revision = "f4a5b6c7d8e9"
down_revision = "e3f4a5b6c7d8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "event_templates",
        sa.Column("id",             sa.Integer,     primary_key=True),
        sa.Column("template_name",  sa.String(100), nullable=False),
        sa.Column("departure_city", sa.String(50),  nullable=True),
        sa.Column("price",          sa.Integer,     nullable=False, server_default="2000"),
        sa.Column("deposit",        sa.Integer,     nullable=False, server_default="300"),
        sa.Column("status",         sa.String(20),  nullable=False, server_default="啟用"),
        sa.Column("created_at",     sa.DateTime,    server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("event_templates")
