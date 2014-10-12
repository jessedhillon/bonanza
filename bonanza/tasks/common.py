import logging
from ConfigParser import ConfigParser

from kombu import Connection, Exchange, Queue
from kombu.pools import connections, producers


logger = logging.getLogger(__name__)
_connections = {}


def configure(config_uri, app_name):
    global _connections

    settings = ConfigParser()
    settings.read([config_uri])
    section = dict(settings.items('kombu:{}'.format(app_name)))
    _connections[app_name] = section['broker_url']
    logger.info("configuring broker {broker_url}".format(**section))


def get_connection(app_name, block=True):
    url = _connections[app_name]
    return connections[Connection(url)].acquire(block)


def get_producer(connection, block=True):
    return producers[connection].acquire(block)


def get_exchange(name, type, **kwargs):
    return Exchange(name, type, **kwargs)


def get_queue(name, exchange, **kwargs):
    return Queue(name, exchange, **kwargs)
