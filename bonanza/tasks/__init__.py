import logging

from kombu.common import maybe_declare
from threading import Thread, Event


logger = logging.getLogger(__name__)


class Task(Thread):
    _exchanges = None
    _queues = None

    def __init__(self, name, broker, **kwargs):
        super(Task, self).__init__(name=name)
        self.broker = broker
        self.channel = broker.channel()
        logger.info("task thread {} initialized".format(self.name))
        for k, v in kwargs.items():
            setattr(self, k, v)
        self._stop = Event()

    def stop(self):
        logger.debug("{} stop".format(self.name))
        self._stop.set()

    @property
    def is_stopped(self):
        return self._stop.isSet()

    def set_exchange(self, name, exchange):
        if self._exchanges is None:
            self._exchanges = {}
        self._exchanges[name] = exchange(self.channel)
        self._exchanges[name].declare()

    def get_exchange(self, name):
        return self._exchanges[name]

    def set_queue(self, name, queue):
        if self._queues is None:
            self._queues = {}
        self._queues[name] = queue.maybe_bind(self.channel)
        maybe_declare(self._queues[name])

    def get_queue(self, name):
        return self._queues[name]
