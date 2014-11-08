import json
from hashlib import sha1

from sqlalchemy.schema import Column
from sqlalchemy.types import Unicode, UnicodeText, Integer, Numeric, Date,\
        Binary
from sqlalchemy.dialects.postgresql import JSON
from geoalchemy2 import Geometry
from batteries.model import Model
from batteries.model.hashable import Hashable, HashableKey
from batteries.model.recordable import Recordable
from batteries.model.geometric import Geometric


class CraigslistListing(Hashable, Recordable, Geometric, Model):
    _key = HashableKey()

    id = Column(Unicode(20), nullable=False, index=True)
    title = Column(UnicodeText, nullable=False)
    relative_url = Column(Unicode(200), nullable=False)
    image_thumbnail_url = Column(Unicode(300))

    bedrooms = Column(Integer, index=True)
    posted_date = Column(Date, nullable=False, index=True)
    ask = Column(Numeric(12, scale=2), nullable=False, index=True)

    location = Column('location', Geometry('POINT', 4269), index=True)
    geocluster_id = Column(Unicode(20), nullable=True, index=True)
    request_token = Column(Binary(16), index=True)

    subdomain = Column(Unicode(100), nullable=False, index=True)
    data = Column(JSON)

    @classmethod
    def make_key(cls, instance):
        j = json.dumps(instance.data)
        return sha1(j).hexdigest()
