"""Add user login tracking fields

Revision ID: 3992511b3906
Revises: 896f3b60763b
Create Date: 2025-03-10 12:37:19.928149

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3992511b3906'
down_revision = '896f3b60763b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('last_login_time', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('login_count', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('last_login_ip', sa.String(length=40), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('last_login_ip')
        batch_op.drop_column('login_count')
        batch_op.drop_column('last_login_time')

    # ### end Alembic commands ###
