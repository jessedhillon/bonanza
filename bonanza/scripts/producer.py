"""Producer for listing sources

Usage:
    producer craigslist <region> <config_uri>
"""

import os
import sys
import signal
import threading
from threading import Event
import time
import json
import random
import logging
from docopt import docopt

import bonanza.scripts.common
import bonanza.tasks.common # flake8: noqa
import bonanza.scripts as scripts
import bonanza.tasks as tasks
from bonanza.tasks.craigslist import JsonSearchTask, UrlProducerTask


logger = logging.getLogger(__name__)


def main(argv=sys.argv):
    try:
        settings = None
        arguments = docopt(__doc__)
        config_uri = arguments['<config_uri>']
        settings = scripts.common.configure(config_uri)

        producer(arguments, settings)

    except Exception:
        if settings is None:
            settings = dict({
                'bonanza.debug': True,
            })
        scripts.common.post_mortem(settings)


def producer(arguments, settings):
    # get the known CL regions
    cwd = os.path.dirname(os.path.realpath(__file__))
    regionfile = open(os.path.join(cwd, 'cl_regions.json'))
    regions = json.loads(regionfile.read())

    # create the broker and tasks
    tasks.common.configure(arguments['<config_uri>'], 'craigslist')
    broker = tasks.common.get_connection('craigslist')

    request_exchange = tasks.common.get_exchange('listing.request', 'topic',
                                                 durable=True)
    request_queue = tasks.common.get_queue('requests_pending',
                                           exchange=request_exchange,
                                           routing_key='listing.request')

    listing_exchange = tasks.common.get_exchange('listing.craigslist', 'topic',
                                                 durable=True)
    listing_queue = tasks.common.get_queue('craigslist_listing', 
                                           exchange=listing_exchange,
                                           routing_key='listing.craigslist')

    channel = broker.channel()
    listing_queue(channel).declare()
    request_queue(channel).declare()

    url_producer = UrlProducerTask("UrlProducer-0", broker, regions=regions)
    url_producer.daemon = True
    url_producer.set_exchange('requests', request_exchange)
    url_producer.set_queue('requests', request_queue)
    url_producer.start()

    request_threads = []
    for i in range(4):
        conn = tasks.common.get_connection('craigslist')
        task = JsonSearchTask("JsonSearch-{}".format(i), conn)
        task.daemon = True
        task.set_exchange('listings', listing_exchange)
        task.set_exchange('requests', request_exchange)
        task.set_queue('requests', request_queue)
        task.set_queue('listings', request_queue)
        request_threads.append(task)

    def signal_handler(signal, frame):
        logger.warn("caught control-C, terminating threads")
        for t in request_threads:
            t.stop()
        url_producer.stop()

    signal.signal(signal.SIGINT, signal_handler)

    for t in request_threads:
        t.start()

    while threading.active_count() > 1:
        time.sleep(0.5)
