import logging

from sqlalchemy.orm import scoped_session, sessionmaker
from zope.sqlalchemy import ZopeTransactionExtension
from batteries.model import Model, initialize_model

logger = logging.getLogger(__name__)
session = None

Model.metadata.naming_convention = {
    'ix': 'ix_%(column_0_label)s',
    'uq': 'uq_%(table_name)s_%(column_0_name)s',
    'ck': 'ck_%(table_name)s_%(constraint_name)s',
    'fk': 'fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s',
    'pk': 'pk_%(table_name)s'
}


def initialize(engine, create=False, drop=False):
    global session
    import bonanza.models.base

    session = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
    initialize_model(session, engine)

    if drop:
        logger.warning("dropping all tables in {engine.url!s}".format(engine=engine))
        Model.metadata.drop_all()

    if create:
        logger.info("creating tables in {engine.url!s}".format(engine=engine))
        Model.metadata.create_all(engine)

    return session
