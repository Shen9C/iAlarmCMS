"""Add active field to User model

Revision ID: 44cb98804b50
Revises: 
Create Date: 2025-03-28 17:53:38.204651

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '44cb98804b50'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('last_login_time', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('token_timestamp', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('active', sa.Boolean(), nullable=True))
        batch_op.alter_column('role',
               existing_type=sa.VARCHAR(length=20),
               type_=sa.String(length=64),
               existing_nullable=True)
        batch_op.alter_column('current_token',
               existing_type=sa.VARCHAR(length=36),
               type_=sa.String(length=128),
               existing_nullable=True)
        batch_op.drop_column('token_expiration')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('token_expiration', sa.FLOAT(), nullable=True))
        batch_op.alter_column('current_token',
               existing_type=sa.String(length=128),
               type_=sa.VARCHAR(length=36),
               existing_nullable=True)
        batch_op.alter_column('role',
               existing_type=sa.String(length=64),
               type_=sa.VARCHAR(length=20),
               existing_nullable=True)
        batch_op.drop_column('active')
        batch_op.drop_column('token_timestamp')
        batch_op.drop_column('last_login_time')

    # ### end Alembic commands ###
