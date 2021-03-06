"""Catching up after reorg

Revision ID: 9b31d50ade9f
Revises: 64466db88199
Create Date: 2017-08-17 12:44:47.550046

"""

# revision identifiers, used by Alembic.
revision = '9b31d50ade9f'
down_revision = '64466db88199'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('custom_tag', 'id')
    op.drop_column('likes', 'id')
    op.drop_column('user_tag', 'id')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user_tag', sa.Column('id', mysql.INTEGER(display_width=11), nullable=False))
    op.add_column('likes', sa.Column('id', mysql.INTEGER(display_width=11), nullable=False))
    op.add_column('custom_tag', sa.Column('id', mysql.INTEGER(display_width=11), nullable=False))
    # ### end Alembic commands ###
