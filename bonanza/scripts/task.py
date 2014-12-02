"""Configures and runs task workers

Usage:
    task <task_name> [--workers=<workers>] [--config=<config>] [--arg=<arg>...] [--sync]

Options:
    -w <workers>, --workers=<workers>   The number of threads to start
    -c <config>, --config=<config>      The path to the configuration file, [default: ./bonanza.ini]
    -a <arg>, --arg=<arg>               Additional configuration argument
    -s, --sync                          Run task synchronously
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

    args = {}
    for a in arguments['--arg']:
        d = util.as_dict(a)
        for k, v in d.items():
            try:
                d[k] = eval(v)
            except:
                pass
        args.update(d)

    task = tasks.common.configure_task(task_name)
    conn = tasks.common.get_connection(task_name)

    if arguments['--sync']:
        logger.info("running one worker synchronously")
        conf = config.copy()
        conf.update(args)
        t = task(task_name, 0, **conf)
        t.connect(conn.clone())
        t.run()
        return

    else:
        threads = []
        signal.signal(signal.SIGINT, make_signal_handler(threads))
        workers = int(arguments['--workers'] or config['task.workers'])
        logger.info("spawning {} worker threads".format(workers))
        for i in range(workers):
            conf = config.copy()
            conf.update(args)

            t = task(task_name, i, daemon=True, **conf)
            t.connect(conn.clone())
            t.start()
            time.sleep(0.8)
            threads.append(t)

    while any([t.is_alive() for t in threads]):
        time.sleep(0.5)


sigint_received = False
def make_signal_handler(threads):
    def signal_handler(signal, frame):
        global sigint_received
        if not sigint_received:
            logger.warn("caught control-C, terminating threads")
            sigint_received = True
            for t in threads:
                t.stop()
        else:
            sys.exit("Interrupt")

    return signal_handler
