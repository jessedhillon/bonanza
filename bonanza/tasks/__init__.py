import logging
import time
from datetime import datetime
from dateutil.rrule import rrule

from kombu.common import maybe_declare
from kombu.utils.limits import TokenBucket
from threading import Thread, Event, Lock


logger = logging.getLogger(__name__)


class Task(Thread):
    exchanges = None
    queues = None

    def __init__(self, task_name, worker_number, connection, **kwargs):
        self.task_name = task_name
        self.worker_number = worker_number
        super(Task, self).__init__()

        self.connection = connection

        logger.info("task thread {} initialized".format(self.name))

        for k, v in kwargs.items():
            setattr(self, k, v)
        self._stop = Event()

    def connect(self):
        self.channel = self.connection.channel()
        self.declare_exchanges()
        self.declare_queues()

    @property
    def name(self):
        vars = {
            'class_name': self.__class__.__name__,
            'task_name': self.task_name,
            'worker_number': self.worker_number,
        }
        return self.name_fmt.format(**vars)

    @classmethod
    def configure(cls, queues, exchanges, **kwargs):
        if 'schedule' in kwargs:
            cls.set_schedule(**kwargs['schedule'])

        if 'rate' in kwargs:
            cls.set_rate(**kwargs['rate'])

        cls.queues = queues
        cls.exchanges = exchanges
        cls.name_fmt = kwargs['thread_name']

    @classmethod
    def set_schedule(cls, **schedule):
        cls.schedule = schedule

    @classmethod
    def set_rate(cls, rate, capacity):
        cls.token_lock = Lock()
        cls.tokens = TokenBucket(rate, capacity=capacity)

    @property
    def next_occurrence(self):
        rule = rrule(**self.schedule)
        now = datetime.now()

        for dt in rule:
            if dt > now:
                return dt

    def sleep_until(self, t=None):
        if t is None:
            t = self.next_occurrence

        diff = t - datetime.now()

        logger.debug("next occurrence in {:0.0f}s".
                     format(diff.total_seconds()))

        while diff.total_seconds() > 0:
            if self.is_stopped:
                return

            diff = t - datetime.now()
            time.sleep(0.5)

    def sleep_for(self, t, step=0.5):
        logger.debug("sleeping for {:0.0f}s".
                     format(t))

        slept = 0
        while slept < t:
            if self.is_stopped:
                return

            time.sleep(step)
            slept += step

    def acquire_token(self, tokens=1, block=True):
        if not self.tokens:
            raise RuntimeError("{} is not using a token bucket".
                               format(self.name))

        self.token_lock.acquire(True)
        acquired = self.tokens.can_consume(tokens)
        if acquired:
            self.token_lock.release()
            return acquired
        else:
            self.token_lock.release()
            if block:
                acquired = False
                while not acquired:
                    wait = self.tokens.expected_time(tokens)
                    self.sleep_for(wait)

                    if self.is_stopped:
                        return

                    self.token_lock.acquire(True)
                    acquired = self.tokens.can_consume(tokens)
                    self.token_lock.release()

                return acquired

            else:
                return self.tokens.expected_time(tokens)

    def stop(self):
        logger.debug("{} stop".format(self.name))
        self._stop.set()

    @property
    def is_stopped(self):
        return self._stop.isSet()

    def declare_exchanges(self):
        self._exchanges = {}
        for name, exchange in self.exchanges.items():
            ex = exchange(self.channel)
            maybe_declare(ex)
            self._exchanges[name] = ex
            logger.debug("bound exchange {}".format(ex))

    def get_exchange(self, name):
        return self._exchanges[name]

    def declare_queues(self):
        self._queues = {}
        for name, queue in self.queues.items():
            q = queue(self.channel)
            maybe_declare(q)
            self._queues[name] = q
            logger.debug("bound queue {}".format(q))

    def get_queue(self, name):
        return self._queues[name]
