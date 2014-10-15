from numbers import Number


def prefixed_keys(d, prefix):
    get_key = lambda k: k.split(prefix)[-1]
    return dict((get_key(k), v) for k, v in d.items() if k.startswith(prefix))


def as_list(v, delim=','):
    return map(lambda s: s.strip(), v.strip().split(delim))


def as_dict(v):
    lines = as_list(v, delim='\n')
    d = {}
    for k, v in map(lambda l: l.split('='), lines):
        d[k.strip()] = v.strip()

    return d


def as_bool(v):
    if v is None:
        return False

    if isinstance(v, Number):
        return False if v == 0 else True

    if isinstance(v, basestring):
        if v.lower() in ['yes', 'true', 'on', '1']:
            return True

        if v.lower() in ['no', 'false', 'off', '0']:
            return False

    raise ValueError(v)
