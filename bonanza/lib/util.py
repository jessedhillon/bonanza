def prefixed_keys(d, prefix):
    return dict((k.split(prefix)[0], v) for k, v in d.items() if k.startswith(prefix))
