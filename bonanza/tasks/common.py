from celery import Celery
from ConfigParser import ConfigParser
from collections import namedtuple
from pyramid.settings import asbool


_brokers = {}


def configure(config_uri, app_name):
    if app_name in _brokers:
        return _brokers[app_name]

    settings = ConfigParser()
    settings.read([config_uri])
    section = dict(settings.items('celery:{}'.format(app_name)))
    config = get_configuration_object(section)

    celery = Celery(app_name)
    celery.config_from_object(config)
    _brokers[app_name] = celery
    return celery


def get_configuration_object(settings):
    settings = {k.lower(): v for k, v in settings.items()}
    keys = [k.upper() for k in settings.keys()]

    if 'CELERY_ACCEPT_CONTENT' in keys:
        v = _make_list(settings['celery_accept_content'])
        settings['celery_accept_content'] = v

    if 'CELERY_ALWAYS_EAGER' in keys:
        b = asbool(settings['celery_always_eager'])
        settings['celery_always_eager'] = b

    CeleryConfig = namedtuple('CeleryConfig', keys)
    config = CeleryConfig(**{k.upper(): v for k, v in settings.items()})

    return config


def _make_list(s):
    return [w.strip() for w in s.split()]
