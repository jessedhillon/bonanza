import logging
import requests
from requests.exceptions import ConnectionError, HTTPError, ConnectTimeout
import random
from urlparse import urlunsplit
from datetime import datetime
from dateutil.rrule import rrule, DAILY, MINUTELY
from threading import Lock
import time
from sqlalchemy.orm.exc import NoResultFound

from kombu.utils.limits import TokenBucket

from bonanza.tasks import Task
import bonanza.tasks.common as common
import bonanza.models as models
from bonanza.models.base import CraigslistListing


logger = logging.getLogger(__name__)


class UrlProducerTask(Task):
    schedule = {
        'freq': DAILY,
        'byhour': 4,
        'byminute': 0,
        'bysecond': 0,
    }

    @property
    def next_time(self):
        rule = rrule(**self.schedule)
        now = datetime.now()

        for dt in rule:
            if dt > now:
                return dt

    def sleep(self):
        diff = self.next_time - datetime.now()
        logger.info("{} next run in {}s".format(self.name,
                                                diff.total_seconds()))

        while diff.total_seconds() > 0:
            if self.is_stopped:
                return

            diff = self.next_time - datetime.now()
            time.sleep(0.5)

    def run(self):
        first_run = True

        while True:
            if first_run:
                first_run = False
            else:
                self.sleep()
            if self.is_stopped:
                return

            self.process_regions()

    def process_regions(self):
        random.shuffle(self.regions)

        with common.get_producer(self.broker) as producer:
            for i, r in enumerate(self.regions):
                self.produce_region(r, producer)

    def produce_region(self, r, producer):
        logger.info("enqueueing subdomain {}".format(r['region']))

        data = {
            'subdomain': r['region'],
            'endpoint': r['endpoint'],
            'name': r['name'],
            'state': r['state'],
        }
        producer.publish(data,
                         exchange=self.get_exchange('requests'),
                         routing_key='listing.request',
                         declare=[self.get_queue('requests')])


class JsonSearchTask(Task):
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux i686) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/37.0.2062.120 Safari/537.36',
    }
    token_lock = Lock()
    tokens = TokenBucket(0.25, capacity=3)

    def run(self):
        with self.broker.Consumer(self.get_queue('requests'), callbacks=[self.receive]):
            while True:
                if self.is_stopped:
                    return
                self.broker.drain_events()

    def acquire_token(self, block=True):
        self.token_lock.acquire()
        if self.tokens.can_consume():
            self.token_lock.release()
            return True
        else:
            self.token_lock.release()
            if block:
                wait = self.tokens.expected_time()
                time.sleep(wait)
                self.acquire_token(block)
            else:
                return self.tokens.expected_time()

    def receive(self, body, message):
        self.acquire_token()

        url = self.make_url(body['subdomain'], body['endpoint'])
        extra = {
            'endpoint': body['endpoint'],
            'subdomain': body['subdomain']
        }

        if body.get('geocluster_id'):
            extra['geocluster_id'] = body['geocluster_id']
            logger.debug("processing geocluster", extra=extra)
        else:
            logger.info("processing subdomain {subdomain}".format(**body),
                        extra=extra)

        try:
            r = requests.get(url, headers=self.headers)

            if not body.get('geocluster_id'):
                count = len(r.json()[0])
                logger.info("processing {} results".format(count), extra={
                    'count': count
                })

            for l in r.json()[0]:
                if 'GeoCluster' in l:
                    data = {
                        'subdomain': body['subdomain'],
                        'endpoint': l['url'],
                        'name': body['name'],
                        'state': body['state'],
                        'geocluster_id': l['GeoCluster']
                    }

                    with common.get_producer(self.broker) as producer:
                        producer.publish(
                            data,
                            exchange=self.get_exchange('requests'),
                            routing_key='listing.request',
                            declare=[self.get_exchange('requests'),
                                     self.get_queue('requests')])
                else:
                    data = {
                        'subdomain': body['subdomain'],
                        'data': l,
                    }

                    with common.get_producer(self.broker) as producer:
                        producer.publish(
                            data,
                            exchange=self.get_exchange('listings'),
                            routing_key='listing.craigslist',
                            declare=[self.get_exchange('listings'),
                                     self.get_queue('listings')])

            message.ack()
        except (HTTPError, ConnectionError, ConnectTimeout):
            logger.exception("request exception")

    @staticmethod
    def make_url(subdomain, endpoint):
        return urlunsplit(("http", "{}.craigslist.org".format(subdomain),
                           endpoint, "", ""))


class ListingConsumerTask(Task):
    srid = 4326

    def __init__(self, *args, **kwargs):
        super(ListingConsumerTask, self).__init__(*args, **kwargs)
        self.conn = models.engine.connect()
        self.session = models.Session(bind=self.conn)

    def run(self):
        with self.broker.Consumer(self.get_queue('listings'), callbacks=[self.receive]):
            while True:
                if self.is_stopped:
                    break
                self.broker.drain_events()

        self.session.close()
        self.conn.close()

    def receive(self, body, message):
        data = body['data']
        subdomain = body['subdomain']

        listing_id = data['PostingID']
        listing = self.get_listing_by_id(listing_id)
        if listing is not None:
            self.update_listing(subdomain, listing, data)
        else:
            listing = self.insert_listing(subdomain, data)

        self.session.add(listing)
        self.session.commit()
        message.ack()

    def get_listing_by_id(self, listing_id):
        try:
            return self.session.query(CraigslistListing).\
                filter_by(id=listing_id).one()
        except NoResultFound:
            return None

    def update_listing(self, subdomain, listing, data):
        logger.debug("updating listing {PostingID}".format(**data), extra={'listing_data': data})
        self.copy_json(listing, data)
        listing.subdomain = subdomain

    def insert_listing(self, subdomain, data):
        logger.debug("inserting listing {PostingID}".format(**data), extra={'listing_data': data})
        listing = CraigslistListing()
        self.copy_json(listing, data)
        listing.subdomain = subdomain
        return listing

    def copy_json(self, listing, data):
        listing.id = data['PostingID']
        listing.title = data['PostingTitle']
        listing.relative_url = data['PostingURL']
        listing.image_thumbnail_url = data.get('ImageThumb')
        listing.bedrooms = self.parse_int(data['Bedrooms'])
        listing.posted_date = self.parse_date(data['PostedDate'])
        listing.ask = self.parse_float(data['Ask'])
        listing.location = (map(self.parse_float,
                               (data['Longitude'], data['Latitude'])),
                            self.srid)
        listing.data = data

        return listing

    def parse_date(self, v):
        return datetime.fromtimestamp(int(v)).date()

    def parse_int(self, v):
        if v.isdigit():
            i = int(v)
            if i < 1:
                return None
            return i
        return None

    def parse_float(self, v):
        try:
            return float(v)
        except ValueError:
            return None
