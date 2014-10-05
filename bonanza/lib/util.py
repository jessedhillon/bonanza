def prefixed_keys(d, prefix):
    make_pair = lambda k, v: (k.split(prefix)[0], v)
    return dict(make_pair(k, v) for k, v in d.items() if k.startswith(prefix))
