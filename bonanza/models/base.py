import json
from hashlib import sha1

from sqlalchemy.orm import relationship
from sqlalchemy.schema import Column, Index, ForeignKeyConstraint
from sqlalchemy.types import Unicode, UnicodeText, Integer, Numeric,\
    Date, Binary
from sqlalchemy.dialects.postgresql import JSON
from geoalchemy2 import Geometry
from batteries.model import Model
from batteries.model.hashable import Hashable, HashableKey
from batteries.model.recordable import Recordable
from batteries.model.geometric import Geometric


class CraigslistListing(Hashable, Recordable, Geometric, Model):
    __table_args__ = (
        Index('ix_craigslist_listing_location', 'location',
              postgresql_using='gist'),
        ForeignKeyConstraint(['state_fp', 'county_fp', 'tract_ce', 'block_ce'],
                             ['census_block.state_fp',
                              'census_block.county_fp',
                              'census_block.tract_ce',
                              'census_block.block_ce'],
                             name='fk_craigslist_listing_census_block'))

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

    state_fp = Column(Unicode(2), nullable=False)
    county_fp = Column(Unicode(3), nullable=False)
    tract_ce = Column(Unicode(6), nullable=False)
    block_ce = Column(Unicode(1), nullable=False)

    census_block = relationship('CensusBlock')

    @classmethod
    def make_key(cls, instance):
        j = json.dumps(instance.data)
        return sha1(j).hexdigest()


class HomepathListing(Hashable, Recordable, Geometric, Model):
    __table_args__ = (
        Index('ix_homepath_listing_location', 'location',
              postgresql_using='gist'),
        ForeignKeyConstraint(['state_fp', 'county_fp', 'tract_ce', 'block_ce'],
                             ['census_block.state_fp',
                              'census_block.county_fp',
                              'census_block.tract_ce',
                              'census_block.block_ce'],
                             name='fk_homepath_listing_census_block'))

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

    state_fp = Column(Unicode(2), nullable=False)
    county_fp = Column(Unicode(3), nullable=False)
    tract_ce = Column(Unicode(6), nullable=False)
    block_ce = Column(Unicode(1), nullable=False)

    census_block = relationship('CensusBlock')


# http://proximityone.com/dataresources/guide/index.html?tl_2013_stcty_bg.htm
class CensusBlock(Geometric, Model):
    __identifiers__ = ('state_name', 'county_fp', 'tract_ce', 'block_ce')
    __table_args__ = (Index('ix_census_block_geometry', 'geometry',
                            postgresql_using='gist'),)

    states_by_fips = {
        '01': {'abbreviation':'AL', 'name': 'Alabama'},
        '02': {'abbreviation':'AK', 'name': 'Alaska'},
        '04': {'abbreviation':'AZ', 'name': 'Arizona'},
        '05': {'abbreviation':'AR', 'name': 'Arkansas'},
        '06': {'abbreviation':'CA', 'name': 'California'},
        '08': {'abbreviation':'CO', 'name': 'Colorado'},
        '09': {'abbreviation':'CT', 'name': 'Connecticut'},
        '10': {'abbreviation':'DE', 'name': 'Delaware'},
        '11': {'abbreviation':'DC', 'name': 'District OF Columbia'},
        '12': {'abbreviation':'FL', 'name': 'Florida'},
        '13': {'abbreviation':'GA', 'name': 'Georgia'},
        '15': {'abbreviation':'HI', 'name': 'Hawaii'},
        '16': {'abbreviation':'ID', 'name': 'Idaho'},
        '17': {'abbreviation':'IL', 'name': 'Illinois'},
        '18': {'abbreviation':'IN', 'name': 'Indiana'},
        '19': {'abbreviation':'IA', 'name': 'Iowa'},
        '20': {'abbreviation':'KS', 'name': 'Kansas'},
        '21': {'abbreviation':'KY', 'name': 'Kentucky'},
        '22': {'abbreviation':'LA', 'name': 'Louisiana'},
        '23': {'abbreviation':'ME', 'name': 'Maine'},
        '24': {'abbreviation':'MD', 'name': 'Maryland'},
        '25': {'abbreviation':'MA', 'name': 'Massachusetts'},
        '26': {'abbreviation':'MI', 'name': 'Michigan'},
        '27': {'abbreviation':'MN', 'name': 'Minnesota'},
        '28': {'abbreviation':'MS', 'name': 'Mississippi'},
        '29': {'abbreviation':'MO', 'name': 'Missouri'},
        '30': {'abbreviation':'MT', 'name': 'Montana'},
        '31': {'abbreviation':'NE', 'name': 'Nebraska'},
        '32': {'abbreviation':'NV', 'name': 'Nevada'},
        '33': {'abbreviation':'NH', 'name': 'New Hampshire'},
        '34': {'abbreviation':'NJ', 'name': 'New Jersey'},
        '35': {'abbreviation':'NM', 'name': 'New Mexico'},
        '36': {'abbreviation':'NY', 'name': 'New York'},
        '37': {'abbreviation':'NC', 'name': 'North Carolina'},
        '38': {'abbreviation':'ND', 'name': 'North Dakota'},
        '39': {'abbreviation':'OH', 'name': 'Ohio'},
        '40': {'abbreviation':'OK', 'name': 'Oklahoma'},
        '41': {'abbreviation':'OR', 'name': 'Oregon'},
        '42': {'abbreviation':'PA', 'name': 'Pennsylvania'},
        '44': {'abbreviation':'RI', 'name': 'Rhode Island'},
        '45': {'abbreviation':'SC', 'name': 'South Carolina'},
        '46': {'abbreviation':'SD', 'name': 'South Dakota'},
        '47': {'abbreviation':'TN', 'name': 'Tennessee'},
        '48': {'abbreviation':'TX', 'name': 'Texas'},
        '49': {'abbreviation':'UT', 'name': 'Utah'},
        '50': {'abbreviation':'VT', 'name': 'Vermont'},
        '51': {'abbreviation':'VA', 'name': 'Virginia'},
        '53': {'abbreviation':'WA', 'name': 'Washington'},
        '54': {'abbreviation':'WV', 'name': 'West Virginia'},
        '55': {'abbreviation':'WI', 'name': 'Wisconsin'},
        '56': {'abbreviation':'WY', 'name': 'Wyoming'},
        '60': {'abbreviation':'AS', 'name': 'American Samoa'},
        '66': {'abbreviation':'GU', 'name': 'Guam'},
        '72': {'abbreviation':'PR', 'name': 'Puerto Rico'},
        '78': {'abbreviation':'VI', 'name': 'Virgin Islands'},
    }

    state_fp = Column(Unicode(2), primary_key=True)
    county_fp = Column(Unicode(3), primary_key=True)
    tract_ce = Column(Unicode(6), primary_key=True)
    block_ce = Column(Unicode(1), primary_key=True)

    geometry = Column(Geometry('MULTIPOLYGON', 4326, spatial_index=False))

    @property
    def geo_id(self):
        return "{state_fp}{county_fp}{tract_ce}{block_ce}"\
               .format(**self.__dict__)

    @property
    def state_name(self):
        return CensusBlock.states_by_fips\
                          .get(self.state_fp, {})\
                          .get('name')

    @property
    def state_abbreviation(self):
        return CensusBlock.states_by_fips\
                          .get(self.state_fp, {})\
                          .get('abbreviation')
