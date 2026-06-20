"""add concert module tables

Revision ID: a1b2c3d4e5f6
Revises: d1306f6cc087
Create Date: 2026-06-15

新增演唱會商機分析平台所需資料表。
不影響任何現有資料表。所有操作均可完整 rollback。
"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = 'd1306f6cc087'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'concerts',
        sa.Column('id',           sa.Integer(), primary_key=True),
        sa.Column('artist',       sa.String(100), nullable=False),
        sa.Column('name',         sa.String(200), nullable=False),
        sa.Column('concert_date', sa.Date(),      nullable=True),
        sa.Column('city',         sa.String(50),  nullable=True),
        sa.Column('venue',        sa.String(200), nullable=True),
        sa.Column('status',       sa.String(20),  nullable=False, server_default='評估中'),
        sa.Column('created_at',   sa.DateTime(),  nullable=True),
        sa.Column('updated_at',   sa.DateTime(),  nullable=True),
    )

    op.create_table(
        'concert_metrics',
        sa.Column('id',               sa.Integer(), primary_key=True),
        sa.Column('concert_id',       sa.Integer(), sa.ForeignKey('concerts.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('popularity_score', sa.Float(),   nullable=True),
        sa.Column('opportunity_score',sa.Float(),   nullable=True),
        sa.Column('est_passengers',   sa.Integer(), nullable=True),
        sa.Column('est_revenue',      sa.Integer(), nullable=True),
        sa.Column('notes',            sa.Text(),    nullable=True),
        sa.Column('updated_at',       sa.DateTime(),nullable=True),
    )

    op.create_table(
        'concert_opportunities',
        sa.Column('id',          sa.Integer(), primary_key=True),
        sa.Column('concert_id',  sa.Integer(), sa.ForeignKey('concerts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('category',    sa.String(50),  nullable=True),
        sa.Column('description', sa.Text(),      nullable=True),
        sa.Column('priority',    sa.String(20),  server_default='中'),
        sa.Column('created_at',  sa.DateTime(),  nullable=True),
    )

    op.create_table(
        'event_groups',
        sa.Column('id',               sa.Integer(), primary_key=True),
        sa.Column('concert_id',       sa.Integer(), sa.ForeignKey('concerts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('group_name',       sa.String(200), nullable=False),
        sa.Column('departure_date',   sa.Date(),    nullable=True),
        sa.Column('vehicle_type',     sa.String(50),server_default='minibus'),
        sa.Column('seat_limit',       sa.Integer(), server_default='8'),
        sa.Column('price_per_person', sa.Integer(), server_default='2000'),
        sa.Column('status',           sa.String(20),server_default='草稿'),
        sa.Column('notes',            sa.Text(),    nullable=True),
        sa.Column('created_at',       sa.DateTime(),nullable=True),
    )


def downgrade():
    op.drop_table('event_groups')
    op.drop_table('concert_opportunities')
    op.drop_table('concert_metrics')
    op.drop_table('concerts')
