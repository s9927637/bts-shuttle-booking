"""add business_insights table

Revision ID: k9e0f1a2b3c4
Revises: j8d9e0f1a2b3
Create Date: 2026-06-21
"""
from alembic import op
import sqlalchemy as sa

revision = "k9e0f1a2b3c4"
down_revision = "j8d9e0f1a2b3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "business_insights",
        sa.Column("id",                  sa.Integer,      primary_key=True),
        sa.Column("concert_hub_id",      sa.Integer,      sa.ForeignKey("concert_data_hub.id", ondelete="CASCADE"), nullable=False, index=True),

        # 分項分數（各 0–100）
        sa.Column("opportunity_score",   sa.Integer,      nullable=False, default=0),
        sa.Column("demand_score",        sa.Integer,      nullable=False, default=0),
        sa.Column("historical_score",    sa.Integer,      nullable=False, default=0),
        sa.Column("competition_score",   sa.Integer,      nullable=False, default=0),
        sa.Column("profitability_score", sa.Integer,      nullable=False, default=0),

        # 預估值
        sa.Column("estimated_passengers", sa.Integer,     nullable=False, default=0),
        sa.Column("estimated_vehicles",   sa.Integer,     nullable=False, default=0),
        sa.Column("estimated_revenue",    sa.Integer,     nullable=False, default=0),
        sa.Column("estimated_profit",     sa.Integer,     nullable=False, default=0),

        # 決策輸出
        sa.Column("recommendation",      sa.String(30),   nullable=False, default="OBSERVE"),
        sa.Column("risk_level",          sa.String(20),   nullable=False, default="MEDIUM"),
        sa.Column("notes",               sa.Text,         nullable=True),

        sa.Column("created_at",          sa.DateTime,     nullable=True),
        sa.Column("updated_at",          sa.DateTime,     nullable=True),
    )


def downgrade():
    op.drop_table("business_insights")
