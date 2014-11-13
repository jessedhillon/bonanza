import os
import logging
from ConfigParser import ConfigParser
from dateutil.rrule import YEARLY, MONTHLY, WEEKLY, DAILY, HOURLY, MINUTELY,\
    SECONDLY, MO, TU, WE, TH, FR, SA, SU

from pyramid.path import DottedNameResolver
from kombu import Connection, Exchange, Queue
from kombu.pools import connections, producers

import bonanza.lib.util as util


logger = logging.getLogger(__name__)
_connections = {}
_exchanges = {}
_queues = {}
_config = {}


def configure(config_uri, task_name):
    global _connections
    global _config

    settings = ConfigParser()
    settings.read([config_uri])
    params = {
        'here': os.path.dirname(os.path.realpath(config_uri))
    }
    config = dict(settings.items('task', False, params))
    task_config = dict(settings.items('task:{}'.format(task_name),
                                      False, params))
    config.update(task_config)

    for k in params.keys():
        del config[k]

    kombu = util.prefixed_keys(config, 'kombu.')
    _connections[task_name] = kombu['broker_url']
    logger.info("configuring broker {broker_url}".format(**kombu))

    for s in settings.sections():
        if s.startswith('exchange:'):
            name = s.split(':')[-1]
            section = dict(settings.items(s, vars=params))
            del section['here']
            configure_exchange(name, section)

    for s in settings.sections():
        if s.startswith('queue:'):
            name = s.split(':')[-1]
            section = dict(settings.items(s, vars=params))
            del section['here']
            configure_queue(name, section)

    _config[task_name] = config
    return config


def configure_task(task_name, workers):
    global _config

    config = _config[task_name]
    tc = util.prefixed_keys(config, 'kombu.')
    tc.update(util.prefixed_keys(config, 'task.'))

    resolver = DottedNameResolver()
    cls = resolver.resolve(tc['class'])

    if 'queues' in tc:
        tc['queues'] = dict(
            (k, get_queue(q)) for k, q in util.as_dict(tc['queues']).items())
    else:
        tc['exchanges'] = {}

    if 'exchanges' in tc:
        tc['exchanges'] = dict(
            (e, get_exchange(e)) for e in util.as_list(tc['exchanges']))
    else:
        tc['exchanges'] = {}

    if 'schedule' in tc:
        tc['schedule'] = _parse_schedule(util.as_dict(tc['schedule']))

    if 'rate' in tc:
        tc['rate'] = {
            'rate': float(tc['rate'].strip()),
            'capacity': workers  # TODO: make this configurable
        }

    cls.configure(**tc)
    return cls


def configure_exchange(name, section):
    global _exchanges
    logger.info("configuring exchange {}".format(name))
    _exchanges[name] = Exchange(name, **section)


def configure_queue(name, section):
    global _queues
    exchange = get_exchange(section['exchange'])
    logger.info("configuring queue {} on exchange {}".
                format(name, exchange.name))

    del section['exchange']
    _queues[name] = Queue(name, exchange=exchange, **section)


def get_connection(task_name, block=True):
    url = _connections[task_name]
    return connections[Connection(url)].acquire(block)


def get_producer(connection, block=True):
    return producers[connection].acquire(block)


def get_exchange(name):
    global _exchanges
    return _exchanges[name]


def get_queue(name):
    global _queues
    return _queues[name]


def _parse_schedule(sched):
    freqs = {
        'yearly': YEARLY,
        'monthly': MONTHLY,
        'daily': DAILY,
        'weekly': WEEKLY,
        'hourly': HOURLY,
        'minutely': MINUTELY,
        'secondly': SECONDLY
    }

    days = {
        'monday': MO,
        'tuesday': TU,
        'wednesday': WE,
        'thursday': TH,
        'friday': FR,
        'saturday': SA,
        'sunday': SU
    }

    if 'freq' in sched:
        f = sched['freq'].lower()
        sched['freq'] = freqs[f]

    if 'byweekday' in sched:
        d = sched['byweekday'].lower()
        sched['byweekday'] = [days.get(day) for day in util.as_list(d)]

    for k, v in sched.items():
        if isinstance(v, basestring):
            sched[k] = int(v)

    return sched


def post_mortem():
    if logger:
        logger.exception(u"unhandled exception")
