import os

from pyramid.httpexceptions import HTTPNotFound
from pyramid.resource import abspath_from_asset_spec

paths = {
    'scss': 'bonanza:assets/scss'
}

def get_css(root, request):
    return _load_asset(request.matchdict['stylesheet'] + '.scss', 'scss').read()

def _load_asset(filename, type):
    path = abspath_from_asset_spec(os.path.join(paths.get(type), filename))

    if not os.path.exists(path):
        raise HTTPNotFound()

    return open(path)
