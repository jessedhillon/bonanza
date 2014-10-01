"""Consumer for listing sources

Usage:
    consumer craigslist <region> [--regions] <config_uri>

Options:
    -r --regions FILE    read region definitions from FILE
"""

import os
import sys
import json
from docopt import docopt

import bonanza.scripts.common
import bonanza.tasks.common
import bonanza.scripts as scripts
import bonanza.tasks as tasks
import bonanza.tasks.craigslist as craigslist


def main(argv=sys.argv):
    try:
        settings = None
        arguments = docopt(__doc__)
        config_uri = arguments['<config_uri>']
        settings = scripts.common.configure(config_uri)

        consumer(arguments, settings)

    except Exception as e:
        if settings is None:
            settings = dict({
                'bonanza.debug': True,
            })
        scripts.common.post_mortem(settings)


def consumer(arguments, settings):
    # get the known CL regions
    if arguments.get('--regions') is None:
        cwd = os.path.dirname(os.path.realpath(__file__))
        regionfile = open(os.path.join(cwd, 'cl_regions.json'))
        regions = json.loads(regionfile.read())

    # create the broker and tasks
    broker = tasks.common.configure(arguments['<config_uri>'], 'craigslist')
    task = craigslist.JsonSearchTask()

    for i, r in enumerate(regions):
        if i > 0:
            break
        task.run(**r)
        # task.delay([
        #     r['region'],
        #     r['endpoint'],
        #     r['name'],
        #     r['state']
        # ])

    broker.start(['celery', 'worker'])
    import pdb; pdb.set_trace()
