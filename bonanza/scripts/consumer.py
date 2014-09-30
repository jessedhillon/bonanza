"""Consumer for listing sources

Usage:
    consumer craigslist <region> [--regions] <config_uri>

Options:
    -r --region FILE    read region definitions from FILE
"""

import sys
from docopt import docopt
import bonanza.scripts.common as common


def main(argv=sys.argv):
    try:
        settings = None
        arguments = docopt(__doc__)
        config_uri = arguments.get('<config_uri>')
        settings = common.configure(config_uri)

        consumer(arguments, settings)

    except Exception as e:
        if settings is None:
            settings = dict({
                'bonanza.debug': True,
            })
        common.post_mortem(settings)


def consumer(arguments, settings):
    import pdb; pdb.set_trace()
