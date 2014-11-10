import json
from hashlib import sha1

from sqlalchemy.schema import Column, Index
from sqlalchemy.types import Unicode, UnicodeText, Integer, Numeric,\
    Date, Binary
from sqlalchemy.dialects.postgresql import JSON
from geoalchemy2 import Geometry
from batteries.model import Model
from batteries.model.hashable import Hashable, HashableKey
from batteries.model.recordable import Recordable
from batteries.model.geometric import Geometric


class CraigslistListing(Hashable, Recordable, Geometric, Model):
    __table_args__ = (Index('ix_craigslist_listing_location', 'location',
                            postgresql_using='gist'),)

    _key = HashableKey()

    id = Column(Unicode(20), nullable=False, index=True)
    title = Column(UnicodeText, nullable=False)
    relative_url = Column(Unicode(200), nullable=False)
    image_thumbnail_url = Column(Unicode(300))

    bedrooms = Column(Integer, index=True)
    posted_date = Column(Date, nullable=False, index=True)
    ask = Column(Numeric(12, scale=2), nullable=False, index=True)

    location = Column('location', Geometry('POINT', 4326, spatial_index=False))
    geocluster_id = Column(Unicode(20), nullable=True, index=True)
    request_token = Column(Binary(16), index=True)

    subdomain = Column(Unicode(100), nullable=False, index=True)
    data = Column(JSON)

    @classmethod
    def make_key(cls, instance):
        j = json.dumps(instance.data)
        return sha1(j).hexdigest()


class HomepathListing(Hashable, Recordable, Geometric, Model):
    __table_args__ = (Index('ix_homepath_listing_location', 'location',
                            postgresql_using='gist'),)

    _key = HashableKey()

    id = Column(Unicode(20), nullable=False, index=True)

    baths = Column(Integer, index=True)
    beds = Column(Integer, index=True)
    price = Column(Numeric(18, scale=2), nullable=False, index=True)
    status = Column(Unicode(20), nullable=False, index=True)
    image_url = Column(Unicode(300))

    location = Column(Geometry('POINT', 4326, spatial_index=False))
    entry_date = Column(Date, nullable=False, index=True)

    property_type = Column(Unicode(10), nullable=False, index=True)
    street = Column(Unicode(200), nullable=False)
    city = Column(Unicode(100), nullable=False)
    state = Column(Unicode(8), nullable=False, index=True)

    request_token = Column(Binary(16), index=True)
    data = Column(JSON)


# http://proximityone.com/dataresources/guide/index.html?tl_2013_stcty_bg.htm
class CensusBlock(Geometric, Model):
    __table_args__ = (Index('ix_census_block_geometry', 'geometry',
                            postgresql_using='gist'),)

    state_fp = Column(Unicode(2), primary_key=True)
    county_fp = Column(Unicode(3), primary_key=True)
    tract_ce = Column(Unicode(6), primary_key=True)
    block_ce = Column(Unicode(1), primary_key=True)

    geometry = Column(Geometry('MULTIPOLYGON', 4326, spatial_index=False))
