from sqlalchemy.ext.associationproxy import association_proxy, AssociationProxy
from sqlalchemy.orm import relation
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy.schema import ForeignKey, Column, Index, UniqueConstraint, ForeignKeyConstraint
from sqlalchemy.sql import and_, or_, not_, null
from sqlalchemy.sql.expression import desc, asc
from sqlalchemy.types import *
from geoalchemy2 import Geometry
from batteries.model import Model
from batteries.model.hashable import Hashable, HashableKey, HashableReference
from batteries.model.recordable import Recordable
from batteries.model.types import UTCDateTime, UUID


class Listing(Hashable, Recordable, Model):
    _key = HashableKey()

    location = Column(Geometry('POINT'))
