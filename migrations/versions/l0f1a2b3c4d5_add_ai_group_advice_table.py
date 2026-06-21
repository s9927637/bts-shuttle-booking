"""add ai_group_advice table

Revision ID: l0f1a2b3c4d5
Revises: k9e0f1a2b3c4
Create Date: 2026-06-21

"""
from alembic import op
import sqlalchemy as sa

revision = 'l0f1a2b3c4d5'
down_revision = 'k9e0f1a2b3c4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'ai_group_advice',
        sa.Column('id',                         sa.Integer(),    nullable=False),
        sa.Column('concert_hub_id',             sa.Integer(),    nullable=False),
        sa.Column('business_insight_id',        sa.Integer(),    nullable=True),
        sa.Column('recommended_price',          sa.Integer(),    nullable=False, server_default='2000'),
        sa.Column('recommended_deposit',        sa.Integer(),    nullable=False, server_default='300'),
        sa.Column('recommended_departure_city', sa.String(50),   nullable=True),
        sa.Column('recommended_vehicle_count',  sa.Integer(),    nullable=False, server_default='1'),
        sa.Column('recommended_passenger_count',sa.Integer(),    nullable=False, server_default='0'),
        sa.Column('risk_level',                 sa.String(20),   nullable=False, server_default='MEDIUM'),
        sa.Column('confidence_score',           sa.Integer(),    nullable=False, server_default='0'),
        sa.Column('summary',                    sa.Text(),       nullable=True),
        sa.Column('created_at',                 sa.DateTime(),   nullable=True),
        sa.Column('updated_at',                 sa.DateTime(),   nullable=True),
        sa.ForeignKeyConstraint(['concert_hub_id'],      ['concert_data_hub.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['business_insight_id'], ['business_insights.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_ai_group_advice_concert_hub_id', 'ai_group_advice', ['concert_hub_id'])


def downgrade():
    op.drop_index('ix_ai_group_advice_concert_hub_id', table_name='ai_group_advice')
    op.drop_table('ai_group_advice')
