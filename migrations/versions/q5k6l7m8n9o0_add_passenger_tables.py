"""add passenger_profiles and passenger_tags tables

Revision ID: q5k6l7m8n9o0
Revises: p4j5k6l7m8n9
Create Date: 2026-06-21

乘客管理中心：
- passenger_profiles：以 phone 為唯一識別，快取統計數字
- passenger_tags：乘客標籤（VIP / 高回購 / 未付款 / 黑名單 / 高價值客戶…）

不修改 orders 結構，不影響 BTS 訂單。
"""
from alembic import op
import sqlalchemy as sa

revision = 'q5k6l7m8n9o0'
down_revision = 'p4j5k6l7m8n9'
branch_labels = None
depends_on = None


def upgrade():
    # ── passenger_profiles ─────────────────────────────────────────────────
    op.create_table(
        'passenger_profiles',
        sa.Column('id',            sa.Integer(),     nullable=False),
        sa.Column('name',          sa.String(100),   nullable=False),
        sa.Column('phone',         sa.String(30),    nullable=False),
        sa.Column('line_user_id',  sa.String(100),   nullable=True),
        sa.Column('display_name',  sa.String(100),   nullable=True),
        sa.Column('total_orders',  sa.Integer(),     nullable=False, server_default='0'),
        sa.Column('total_events',  sa.Integer(),     nullable=False, server_default='0'),
        sa.Column('total_spent',   sa.Integer(),     nullable=False, server_default='0'),
        sa.Column('last_order_at', sa.DateTime(),    nullable=True),
        sa.Column('created_at',    sa.DateTime(),    nullable=True),
        sa.Column('updated_at',    sa.DateTime(),    nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('phone', name='uq_passenger_profile_phone'),
    )
    op.create_index('ix_passenger_profiles_phone',        'passenger_profiles', ['phone'])
    op.create_index('ix_passenger_profiles_line_user_id', 'passenger_profiles', ['line_user_id'])

    # ── passenger_tags ──────────────────────────────────────────────────────
    op.create_table(
        'passenger_tags',
        sa.Column('id',           sa.Integer(),   nullable=False),
        sa.Column('passenger_id', sa.Integer(),   nullable=False),
        sa.Column('tag_name',     sa.String(50),  nullable=False),
        sa.Column('created_at',   sa.DateTime(),  nullable=True),
        sa.ForeignKeyConstraint(['passenger_id'], ['passenger_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('passenger_id', 'tag_name', name='uq_passenger_tag'),
    )
    op.create_index('ix_passenger_tags_passenger_id', 'passenger_tags', ['passenger_id'])
    op.create_index('ix_passenger_tags_tag_name',     'passenger_tags', ['tag_name'])


def downgrade():
    op.drop_index('ix_passenger_tags_tag_name',     table_name='passenger_tags')
    op.drop_index('ix_passenger_tags_passenger_id', table_name='passenger_tags')
    op.drop_table('passenger_tags')

    op.drop_index('ix_passenger_profiles_line_user_id', table_name='passenger_profiles')
    op.drop_index('ix_passenger_profiles_phone',        table_name='passenger_profiles')
    op.drop_table('passenger_profiles')
