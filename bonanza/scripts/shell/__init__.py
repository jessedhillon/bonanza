def setup(env):
    import sys
    import atexit
    import os
    import sys
    import transaction
    from pprint import pprint
    import bonanza.scripts.common as common
    import bonanza.models as models

    sys.ps1 = 'py(bonanza)> '
    sys.ps2 = '  (bonanza)> '

    try:
        import readline
    except ImportError:
        print "Module readline not available."
    else:
        import rlcompleter
        readline.parse_and_bind("tab: complete")

    history_path = os.path.expanduser("~/.bonanza_history")

    def save_history(history_path=history_path):
        import readline
        readline.write_history_file(history_path)

    if os.path.exists(history_path):
        readline.read_history_file(history_path)

    atexit.register(save_history)

    # anything not deleted (sys and os) will remain in the interpreter session
    del atexit, readline, rlcompleter, save_history, history_path

    env['pp'] = pprint
    env['configure'] = common.configure
    env['models'] = models
    env['transaction'] = transaction
