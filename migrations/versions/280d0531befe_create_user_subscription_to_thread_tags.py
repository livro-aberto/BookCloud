"""Create user subscription to thread tags

Revision ID: 280d0531befe
Revises: d838fb3c676d
Create Date: 2017-08-21 11:49:46.854898

"""

# revision identifiers, used by Alembic.
revision = '280d0531befe'
down_revision = 'd838fb3c676d'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('user_subscription',
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('named_tag', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['named_tag'], ['named_tag.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], )
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('user_subscription')
    # ### end Alembic commands ###
