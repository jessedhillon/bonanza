"""index timestamps

Revision ID: 56fca517b343
Revises: ecc1ad2d65b
Create Date: 2014-11-01 13:28:31.377508

"""

# revision identifiers, used by Alembic.
revision = '56fca517b343'
down_revision = 'ecc1ad2d65b'

from alembic import op
import sqlalchemy as sa
from batteries.model.types import Ascii, UTCDateTime
from geoalchemy2 import Geometry


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_index(op.f('ix_craigslist_listing_ctime'), 'craigslist_listing', ['ctime'], unique=False)
    op.create_index(op.f('ix_craigslist_listing_mtime'), 'craigslist_listing', ['mtime'], unique=False)
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_craigslist_listing_mtime'), table_name='craigslist_listing')
    op.drop_index(op.f('ix_craigslist_listing_ctime'), table_name='craigslist_listing')
    ### end Alembic commands ###