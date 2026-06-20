"""add event_metrics table

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-06-20

建立 event_metrics 統計快照表。
每個 EventPage 對應一筆（UNIQUE on event_page_id）。
page_views 於使用者造訪活動頁時累計；其餘欄位由
event_metrics_service.refresh_metrics() 重新計算後寫入。
"""
from alembic import op
import sqlalchemy as sa

revision = 'e3f4a5b6c7d8'
down_revision = 'd2e3f4a5b6c7'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'event_metrics',
        sa.Column('id',             sa.Integer(),     nullable=False, primary_key=True),
        sa.Column('event_page_id',  sa.Integer(),     nullable=False),
        sa.Column('page_views',     sa.Integer(),     nullable=False, server_default='0'),
        sa.Column('booking_count',  sa.Integer(),     nullable=False, server_default='0'),
        sa.Column('paid_count',     sa.Integer(),     nullable=False, server_default='0'),
        sa.Column('unpaid_count',   sa.Integer(),     nullable=False, server_default='0'),
        sa.Column('cancelled_count',sa.Integer(),     nullable=False, server_default='0'),
        sa.Column('passenger_count',sa.Integer(),     nullable=False, server_default='0'),
        sa.Column('deposit_amount', sa.Integer(),     nullable=False, server_default='0'),
        sa.Column('revenue_amount', sa.Integer(),     nullable=False, server_default='0'),
        sa.Column('completion_rate',sa.Numeric(5, 2), nullable=False, server_default='0'),
        sa.Column('created_at',     sa.DateTime(),    nullable=True),
        sa.Column('updated_at',     sa.DateTime(),    nullable=True),
        sa.ForeignKeyConstraint(
            ['event_page_id'], ['event_pages.id'],
            name='fk_event_metrics_event_page_id',
            ondelete='CASCADE',
        ),
        sa.UniqueConstraint('event_page_id', name='uq_event_metrics_event_page_id'),
    )
    op.create_index('ix_event_metrics_event_page_id', 'event_metrics', ['event_page_id'])


def downgrade():
    op.drop_index('ix_event_metrics_event_page_id', table_name='event_metrics')
    op.drop_table('event_metrics')
