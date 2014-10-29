"""initial schema

Revision ID: 168d2892efbe
Revises: 000000000000
Create Date: 2014-09-30 12:39:56.044237

"""

# revision identifiers, used by Alembic.
revision = '168d2892efbe'
down_revision = '000000000000'

from alembic import op
import sqlalchemy as sa
from batteries.model.types import Ascii, UTCDateTime
from geoalchemy2 import Geometry


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('listing',
        sa.Column('key', Ascii(length=40), nullable=False),
        sa.Column('location', Geometry(geometry_type='POINT'), nullable=True),
        sa.Column('ctime', UTCDateTime(), nullable=True),
        sa.Column('mtime', UTCDateTime(), nullable=True),
        sa.PrimaryKeyConstraint('key', name=op.f('pk_listing'))
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('listing')
    ### end Alembic commands ###
