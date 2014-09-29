"""Populate bonanza database

Usage:
    populate_bonanza [-c | --create] [-d | --drop] [-s | --schema-only] <config_uri>
    populate_bonanza (-h | --help)

Options:
    -h --help           Show this text
    -c --create         Issue DDLs to create the schema
    -d --drop           Drop existing tables
    -s --schema-only    Only issue DDLs, do not insert base entities, resources
"""

from docopt import docopt

import os
import sys
import transaction
import logging
import warnings

from sqlalchemy import engine_from_config
from pyramid.paster import get_appsettings, setup_logging
from pyramid.settings import asbool

import bonanza.models as models

logger = None

# warnings.filterwarnings('error')

def main(argv=sys.argv):
    arguments = docopt(__doc__)

    config_uri = arguments.get('<config_uri>')
    create = arguments.get('--create')
    drop = arguments.get('--drop')

    setup_logging(config_uri)
    settings = get_appsettings(config_uri)
    logger = logging.getLogger(__name__)

    logger.info("configured with {0}".format(os.path.abspath(config_uri)))

    try:
        engine = engine_from_config(settings, 'sqlalchemy.')
        session = models.initialize(engine, create=create, drop=drop)

        if arguments.get('--schema-only'):
            return

    except Exception as e:
        import traceback
        import sys
        import pdb;

        logger.fatal(u"unhandled exception", exc_info=sys.exc_info())

        if asbool(settings.get('bonanza.debug', 'true')):
            pdb.post_mortem(sys.exc_info()[2])
