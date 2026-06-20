"""add event_pages table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-15

新增活動模板系統 event_pages 資料表。
不影響任何現有資料表。完整可 rollback。
"""
from alembic import op
import sqlalchemy as sa

revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'event_pages',
        sa.Column('id',             sa.Integer(),     primary_key=True),
        sa.Column('title',          sa.String(200),   nullable=False),
        sa.Column('slug',           sa.String(200),   nullable=False),
        sa.Column('artist_name',    sa.String(100),   nullable=False),
        sa.Column('event_name',     sa.String(200),   nullable=False),
        sa.Column('event_date',     sa.String(200),   nullable=True),
        sa.Column('departure_city', sa.String(50),    nullable=True),
        sa.Column('price',          sa.Integer(),     nullable=True,  server_default='2000'),
        sa.Column('deposit',        sa.Integer(),     nullable=True,  server_default='300'),
        sa.Column('cover_image',    sa.String(500),   nullable=True),
        sa.Column('status',         sa.String(20),    nullable=False, server_default='草稿'),
        sa.Column('description',    sa.Text(),        nullable=True),
        sa.Column('faq_content',    sa.Text(),        nullable=True),
        sa.Column('terms_content',  sa.Text(),        nullable=True),
        sa.Column('concert_id',     sa.Integer(),     sa.ForeignKey('concerts.id',     ondelete='SET NULL'), nullable=True),
        sa.Column('event_group_id', sa.Integer(),     sa.ForeignKey('event_groups.id', ondelete='SET NULL'), nullable=True),
        sa.Column('deleted_at',     sa.DateTime(),    nullable=True),
        sa.Column('created_at',     sa.DateTime(),    nullable=True),
        sa.Column('updated_at',     sa.DateTime(),    nullable=True),
    )
    op.create_index('ix_event_pages_slug', 'event_pages', ['slug'], unique=True)


def downgrade():
    op.drop_index('ix_event_pages_slug', table_name='event_pages')
    op.drop_table('event_pages')
