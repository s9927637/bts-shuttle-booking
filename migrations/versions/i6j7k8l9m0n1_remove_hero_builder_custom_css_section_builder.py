"""Architecture Audit follow-up: remove Hero Builder, Custom CSS, Section Builder
(ActivityTemplate + EventSection) — all superseded by Landing Page (Phase 4)

Revision ID: i6j7k8l9m0n1
Revises: h5i6j7k8l9m0
Create Date: 2026-07-06
"""
from alembic import op
import sqlalchemy as sa

revision = 'i6j7k8l9m0n1'
down_revision = 'h5i6j7k8l9m0'
branch_labels = None
depends_on = None


def upgrade():
    # ── Section Builder（Landing Builder）: drop dependent tables first ──
    op.drop_table('activity_template_sections')
    op.drop_table('activity_templates')
    op.drop_table('event_sections')

    # ── Hero Builder: variant selector + layout controls + editorial styling ──
    op.drop_column('event_pages', 'hero_variant')
    op.drop_column('event_pages', 'hero_height')
    op.drop_column('event_pages', 'hero_valign')
    op.drop_column('event_pages', 'hero_width')
    op.drop_column('event_pages', 'hero_overlay')
    op.drop_column('event_pages', 'hero_title_size')
    op.drop_column('event_pages', 'hero_title_color')
    op.drop_column('event_pages', 'hero_subtitle_color')
    op.drop_column('event_pages', 'hero_text_color')
    op.drop_column('event_pages', 'hero_btn_color')

    # ── Custom CSS: superseded by landing_css ──
    op.drop_column('event_pages', 'custom_css')


def downgrade():
    op.add_column('event_pages', sa.Column('custom_css', sa.Text(), nullable=True))

    op.add_column('event_pages', sa.Column('hero_btn_color', sa.String(length=20), nullable=True))
    op.add_column('event_pages', sa.Column('hero_text_color', sa.String(length=20), nullable=True))
    op.add_column('event_pages', sa.Column('hero_subtitle_color', sa.String(length=20), nullable=True))
    op.add_column('event_pages', sa.Column('hero_title_color', sa.String(length=20), nullable=True))
    op.add_column('event_pages', sa.Column('hero_title_size', sa.String(length=10), nullable=True))
    op.add_column('event_pages', sa.Column('hero_overlay', sa.String(length=20), nullable=True))
    op.add_column('event_pages', sa.Column('hero_width', sa.String(length=10), nullable=True))
    op.add_column('event_pages', sa.Column('hero_valign', sa.String(length=10), nullable=True))
    op.add_column('event_pages', sa.Column('hero_height', sa.String(length=10), nullable=True))
    op.add_column('event_pages', sa.Column('hero_variant', sa.String(length=30), nullable=True))

    op.create_table(
        'event_sections',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('event_id', sa.Integer(), sa.ForeignKey('event_pages.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=True),
        sa.Column('content_json', sa.Text(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('show_desktop', sa.Boolean(), nullable=True),
        sa.Column('show_tablet', sa.Boolean(), nullable=True),
        sa.Column('show_mobile', sa.Boolean(), nullable=True),
        sa.Column('theme_style', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'activity_templates',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('theme_color', sa.String(length=30), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'activity_template_sections',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('template_id', sa.Integer(), sa.ForeignKey('activity_templates.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=True),
        sa.Column('content_json', sa.Text(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
