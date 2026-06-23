"""Event Isolation Phase 1-6: announcements/payments event_page_id + faqs table

Revision ID: y3s4t5u6v7w8
Revises: x2r3s4t5u6v7
Create Date: 2026-06-23

"""
from alembic import op
import sqlalchemy as sa

revision = 'y3s4t5u6v7w8'
down_revision = 'x2r3s4t5u6v7'
branch_labels = None
depends_on = None


def upgrade():
    # Phase 2: announcements.event_page_id
    op.add_column('announcements',
        sa.Column('event_page_id', sa.Integer(),
                  sa.ForeignKey('event_pages.id', ondelete='SET NULL'),
                  nullable=True))
    op.create_index('ix_announcements_event_page_id', 'announcements', ['event_page_id'])

    # Phase 3: faqs table
    op.create_table(
        'faqs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('event_page_id', sa.Integer(),
                  sa.ForeignKey('event_pages.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('question', sa.String(500), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_faqs_event_page_id', 'faqs', ['event_page_id'])

    # Phase 6: payments.event_page_id
    op.add_column('payments',
        sa.Column('event_page_id', sa.Integer(),
                  sa.ForeignKey('event_pages.id', ondelete='SET NULL'),
                  nullable=True))
    op.create_index('ix_payments_event_page_id', 'payments', ['event_page_id'])

    # Phase 1 確認: 更新既有 payments.event_page_id 從 order 推導
    op.execute("""
        UPDATE payments
        SET event_page_id = orders.event_page_id
        FROM orders
        WHERE payments.order_id = orders.id
          AND orders.event_page_id IS NOT NULL
          AND payments.event_page_id IS NULL
    """)


def downgrade():
    op.drop_index('ix_payments_event_page_id', table_name='payments')
    op.drop_column('payments', 'event_page_id')

    op.drop_table('faqs')

    op.drop_index('ix_announcements_event_page_id', table_name='announcements')
    op.drop_column('announcements', 'event_page_id')
