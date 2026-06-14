"""add vehicle name, type, driver_id; make driver_name/phone nullable

Revision ID: 7c07dc5449e1
Revises: 844e5a2589e8
Create Date: 2026-06-14

"""
from alembic import op
import sqlalchemy as sa

revision = '7c07dc5449e1'
down_revision = '844e5a2589e8'
branch_labels = None
depends_on = None


def upgrade():
    # 新增 vehicles.name（車輛名稱）
    op.add_column('vehicles', sa.Column('name', sa.String(100), nullable=True))
    # 新增 vehicles.vehicle_type（車型描述，如 Volkswagen Caravelle）
    op.add_column('vehicles', sa.Column('vehicle_type', sa.String(100), nullable=True))
    # 新增 vehicles.driver_id（外鍵關聯 drivers.id）
    op.add_column('vehicles', sa.Column('driver_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_vehicles_driver_id', 'vehicles', 'drivers', ['driver_id'], ['id'], ondelete='SET NULL'
    )
    # 將 driver_name / driver_phone 改為可為空（保留既有資料，向前相容）
    op.alter_column('vehicles', 'driver_name', existing_type=sa.String(100), nullable=True)
    op.alter_column('vehicles', 'driver_phone', existing_type=sa.String(20), nullable=True)


def downgrade():
    op.drop_constraint('fk_vehicles_driver_id', 'vehicles', type_='foreignkey')
    op.drop_column('vehicles', 'driver_id')
    op.drop_column('vehicles', 'vehicle_type')
    op.drop_column('vehicles', 'name')
    op.alter_column('vehicles', 'driver_name', existing_type=sa.String(100), nullable=False)
    op.alter_column('vehicles', 'driver_phone', existing_type=sa.String(20), nullable=False)
