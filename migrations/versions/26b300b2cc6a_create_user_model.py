"""Create user model

Revision ID: 26b300b2cc6a
Revises: 
Create Date: 2025-03-06 21:01:00.747812

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '26b300b2cc6a'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('alarm',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('alarm_number', sa.String(length=50), nullable=False),
    sa.Column('alarm_type', sa.String(length=100), nullable=False),
    sa.Column('alarm_time', sa.DateTime(), nullable=False),
    sa.Column('alarm_image', sa.String(length=255), nullable=True),
    sa.Column('is_processed', sa.Boolean(), nullable=False),
    sa.Column('device_name', sa.String(length=100), nullable=True, comment='设备名称'),
    sa.Column('device_ip', sa.String(length=50), nullable=True, comment='设备IP地址'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('alarm_number')
    )
    op.create_table('system_setting',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('key', sa.String(length=50), nullable=False),
    sa.Column('value', sa.String(length=500), nullable=True),
    sa.Column('description', sa.String(length=200), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('key')
    )
    op.create_table('user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=64), nullable=False),
    sa.Column('password_hash', sa.String(length=128), nullable=False),
    sa.Column('role', sa.String(length=20), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('username')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('user')
    op.drop_table('system_setting')
    op.drop_table('alarm')
    # ### end Alembic commands ###
