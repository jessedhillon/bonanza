from sqlalchemy.ext.associationproxy import association_proxy, AssociationProxy
from sqlalchemy.orm import relation
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy.schema import ForeignKey, Column, Index, UniqueConstraint, ForeignKeyConstraint
from sqlalchemy.sql import and_, or_, not_, null
from sqlalchemy.sql.expression import desc, asc
from sqlalchemy.types import Unicode, UnicodeText, Integer, Numeric, Date
from geoalchemy2 import Geometry
from batteries.model import Model
from batteries.model.hashable import Hashable, HashableKey
from batteries.model.recordable import Recordable
from batteries.model.geometric import Geometric


class CraigslistListing(Hashable, Recordable, Geometric, Model):
    _key = HashableKey()

    id = Column(Unicode(20), nullable=False)
    title = Column(UnicodeText, nullable=False)
    url = Column(Unicode(200), nullable=False)
    image_thumbnail_url = Column(Unicode(300))

    bedrooms = Column(Integer)
    posted_date = Column(Date, nullable=False)
    ask = Column(Numeric(12, scale=2), nullable=False)

    location = Column('location', Geometry('POINT', 4269))
