from pyramid.config import Configurator
from pyramid_jinja2 import renderer_factory
from pyramid_beaker import session_factory_from_settings
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from sqlalchemy import engine_from_config

import bonanza.models as models

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    engine = engine_from_config(settings, 'sqlalchemy.')
    models.initialize(engine)
    config = Configurator(settings=settings,
                          root_factory='bonanza.lib:RootFactory',
                          session_factory=session_factory_from_settings(settings),
                          # authentication_policy=AuthTktAuthenticationPolicy(
                          #     '5e04c5f06208def3c5becd6db74f8d11733a912a',
                          #     callback=bonanza.security.lookup_userid),
                          # authorization_policy=ACLAuthorizationPolicy()
                          )

    config.include('pyramid_jinja2')
    config.include('pyramid_scss')

    config.add_static_view('static', 'bonanza:static', cache_max_age=3600)

    # entity
    config.add_route('home', '/')
    config.add_view(route_name='home', view='bonanza.controllers.home.get_index',
        renderer='/home/index.jinja2', request_method='GET')

    # scss
    config.add_route('css', '/css/{stylesheet}.css')
    config.add_view(route_name='css', view='bonanza.controllers.static.get_css',
        renderer='scss', request_method='GET')

    config.commit()
    add_template_filters(config)
    return config.make_wsgi_app()


def add_template_filters(config):
    import bonanza.lib.filters
    env = config.get_jinja2_environment()

    filters = {}
    for name in dir(bonanza.lib.filters):
        if name.endswith('_filter'):
            filter_name = '_'.join(name.split('_')[:-1])
            filters[filter_name] = getattr(bonanza.lib.filters, name)

    env.filters.update(filters)
