import sys
import logging
import pdb
import pyramid.paster as paster
from pyramid.request import Request
from pyramid.settings import asbool


logger = None


def configure(config_uri, **kwargs):
    global logger
    settings = paster.get_appsettings(config_uri)
    paster.setup_logging(config_uri)
    logger = logging.getLogger(__name__)

    request = kwargs.get('request')
    if request is None and 'base_url' in kwargs:
        request = Request.blank(u'/', base_url=kwargs['base_url'])

    paster.bootstrap(config_uri, request=request)
    return settings


def post_mortem(settings):
    if logger:
        logger.fatal(u"unhandled exception", exc_info=sys.exc_info())

    if asbool(settings.get('bonanza.debug')):
        pdb.post_mortem(sys.exc_info()[2])
