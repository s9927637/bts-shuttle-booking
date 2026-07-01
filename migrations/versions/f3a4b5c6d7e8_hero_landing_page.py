"""Phase 11: Hero Landing Page — hero layout + CTA toggle + activity footer

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-07-01
"""
from alembic import op
import sqlalchemy as sa

revision = 'f3a4b5c6d7e8'
down_revision = 'e2f3a4b5c6d7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('event_pages', sa.Column('hero_height', sa.String(length=10), nullable=True))
    op.add_column('event_pages', sa.Column('hero_valign', sa.String(length=10), nullable=True))
    op.add_column('event_pages', sa.Column('hero_width', sa.String(length=10), nullable=True))
    op.add_column('event_pages', sa.Column('cta_enabled', sa.Boolean(), nullable=True))
    op.add_column('event_pages', sa.Column('footer_enabled', sa.Boolean(), nullable=True))
    op.add_column('event_pages', sa.Column('footer_text', sa.String(length=200), nullable=True))
    op.add_column('event_pages', sa.Column('footer_privacy_url', sa.String(length=300), nullable=True))
    op.add_column('event_pages', sa.Column('footer_terms_url', sa.String(length=300), nullable=True))
    op.add_column('event_pages', sa.Column('footer_contact_url', sa.String(length=300), nullable=True))


def downgrade():
    op.drop_column('event_pages', 'footer_contact_url')
    op.drop_column('event_pages', 'footer_terms_url')
    op.drop_column('event_pages', 'footer_privacy_url')
    op.drop_column('event_pages', 'footer_text')
    op.drop_column('event_pages', 'footer_enabled')
    op.drop_column('event_pages', 'cta_enabled')
    op.drop_column('event_pages', 'hero_width')
    op.drop_column('event_pages', 'hero_valign')
    op.drop_column('event_pages', 'hero_height')
