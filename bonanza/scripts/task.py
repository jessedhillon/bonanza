"""Configures and runs task workers

Usage:
    task <task_name> [--workers=<workers>] [--config=<config>] [--arg=<arg>...]

Options:
    -w <workers>, --workers=<workers>   The number of threads to start
    -c <config>, --config=<config>      The path to the configuration file, [default: ./bonanza.ini]
    -a <arg>, --arg=<arg>               Additional configuration argument
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
import bonanza.lib.util as util


logger = logging.getLogger(__name__)


def main(argv=sys.argv):
    try:
        settings = None
        arguments = docopt(__doc__)
        config_uri = arguments['--config']
        settings = scripts.common.configure(config_uri)

        run_task(arguments, settings)

    except Exception:
        if settings is None:
            settings = dict({
                'bonanza.debug': True,
            })
        scripts.common.post_mortem(settings)


def run_task(arguments, settings):
    task_name = arguments['<task_name>']
    config = tasks.common.configure(arguments['--config'], task_name)
    workers = int(arguments['--workers'] or config['task.workers'])

    args = {}
    for a in arguments['--arg']:
        d = util.as_dict(a)
        for k, v in d.items():
            try:
                d[k] = eval(v)
            except:
                pass
        args.update(d)

    logger.info("starting {} worker threads".format(workers))
    threads = []
    task = tasks.common.configure_task(task_name, workers)
    for i in range(workers):
        conf = config.copy()
        conf.update(args)

        conn = tasks.common.get_connection(task_name)
        t = task(task_name, i, conn, **conf)
        t.daemon = True
        t.start()
        threads.append(t)

    def signal_handler(signal, frame):
        logger.warn("caught control-C, terminating threads")
        for t in threads:
            t.stop()

    signal.signal(signal.SIGINT, signal_handler)

    while threading.active_count() > 1:
        time.sleep(0.5)
