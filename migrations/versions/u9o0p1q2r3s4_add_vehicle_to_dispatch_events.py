"""add vehicle_id to dispatch_events

Revision ID: u9o0p1q2r3s4
Revises: t8n9o0p1q2r3
Create Date: 2026-06-22
"""
from alembic import op
import sqlalchemy as sa

revision = 'u9o0p1q2r3s4'
down_revision = 't8n9o0p1q2r3'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('dispatch_events',
        sa.Column('vehicle_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_dispatch_events_vehicle_id',
        'dispatch_events', 'vehicles',
        ['vehicle_id'], ['id'],
        ondelete='SET NULL',
    )


def downgrade():
    op.drop_constraint('fk_dispatch_events_vehicle_id', 'dispatch_events', type_='foreignkey')
    op.drop_column('dispatch_events', 'vehicle_id')
