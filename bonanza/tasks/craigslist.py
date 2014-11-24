from datetime import datetime
from requests.exceptions import ConnectionError, HTTPError, ConnectTimeout
from socket import timeout
from urlparse import urlunsplit
from uuid import uuid4 as uuid
import base64
import json
import logging
import random
import requests

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import func

from bonanza.models.base import CraigslistListing, CensusBlock
from bonanza.tasks import Task
import bonanza.models as models
import bonanza.tasks.common as common


logger = logging.getLogger(__name__)


class UrlProducerTask(Task):
    run_once = False

    def run(self):
        try:
            while True:
                if not self.run_once:
                    self.sleep_until(self.next_occurrence)

                if self.is_stopped:
                    return

                self.process_regions()
                if self.run_once:
                    self.stop()
        except:
            common.post_portem()

    def process_regions(self):
        with open(self.region_file, 'r') as f:
            regions = json.loads(f.read())
            random.shuffle(regions)

        with self.get_producer() as producer:
            for i, r in enumerate(regions):
                self.produce_region(r, producer)

    def produce_region(self, r, producer):
        logger.info("enqueueing subdomain", extra=dict(region=r))
        data = {
            'subdomain': r['region'],
            'endpoint': r['endpoint'],
            'name': r['name'],
            'state': r['state'],
        }
        producer.publish(
            data,
            exchange=self.get_exchange('requests'),
            routing_key='requests.craigslist.subdomain',
            declare=[self.get_queue('requests')])


class JsonSearchTask(Task):
    geocluster_threshold = 10
    _proxies = []

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux i686) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/39.0.2171.85 Safari/537.36',
    }

    @property
    def proxies(self):
        return self._proxies

    @proxies.setter
    def proxies(self, v):
        import pdb; pdb.set_trace()
        if isinstance(v, basestring):
            v = map(lambda s: s.strip(), v.strip().split("\n"))
        self._proxies = v

    def run(self):
        try:
            with self.get_consumer('requests'):
                while True:
                    if self.is_stopped:
                        return

                    try:
                        self.connection.drain_events(timeout=1)
                    except timeout:
                        pass
        except:
            common.post_mortem()

    def generate_request_token(self):
        return uuid().bytes

    def receive(self, body, message):
        url = self.make_url(body['subdomain'], body['endpoint'])
        extra = {
            'endpoint': body['endpoint'],
            'subdomain': body['subdomain']
        }

        try:
            self.acquire_token()
            token = base64.b64encode(self.generate_request_token())

            r = requests.get(url, headers=self.headers, proxies=self.proxies)

            try:
                results, query = r.json()
            except ValueError:
                logger.exception("json decode error")
                message.requeue()
                return

            extra.update({
                'token': token,
                'count': len(results),
                'query': query,
            })
            if body.get('geocluster_id'):
                extra['geocluster_id'] = body['geocluster_id']
                logger.info("processing geocluster", extra=extra)
            else:
                logger.info("processing subdomain", extra=extra)

            for l in results:
                if 'GeoCluster' in l:
                    if int(l['NumPosts']) >= int(self.geocluster_threshold):
                        data = {
                            '_token': token,
                            'subdomain': body['subdomain'],
                            'endpoint': l['url'],
                            'name': body['name'],
                            'state': body['state'],
                            'geocluster_id': l['GeoCluster']
                        }

                        with self.get_producer() as producer:
                            producer.publish(
                                data,
                                exchange=self.get_exchange('requests'),
                                routing_key='requests.craigslist.geocluster',
                                declare=[
                                    self.get_exchange('requests'),
                                    self.get_queue('requests'),
                                    self.get_queue('geocluster_requests')])
                else:
                    data = {
                        '_token': token,
                        'subdomain': body['subdomain'],
                        'data': l,
                    }

                    if 'geocluster_id' in body:
                        data['geocluster_id'] = body['geocluster_id']

                    with self.get_producer() as producer:
                        producer.publish(
                            data,
                            exchange=self.get_exchange('listings'),
                            routing_key='listings.craigslist',
                            declare=[self.get_exchange('listings'),
                                     self.get_queue('listings')])

            message.ack()

        except (HTTPError, ConnectionError, ConnectTimeout):
            logger.exception("request exception")
            message.requeue()

    @staticmethod
    def make_url(subdomain, endpoint):
        return urlunsplit(("http", "{}.craigslist.org".format(subdomain),
                           endpoint, "", ""))


class ListingProcessorTask(Task):
    srid = 4326

    def __init__(self, *args, **kwargs):
        super(ListingProcessorTask, self).__init__(*args, **kwargs)
        self.sql = models.engine.connect()
        self.session = models.Session(bind=self.sql)

    def run(self):
        try:
            with self.get_consumer('listings'):
                while True:
                    if self.is_stopped:
                        break

                    try:
                        self.connection.drain_events(timeout=1)
                    except timeout:
                        pass

            self.session.close()
            self.sql.close()

        except:
            common.post_mortem()

    def receive(self, body, message):
        data = body['data']
        subdomain = body['subdomain']
        token = base64.b64decode(body['_token']) if '_token' in body else None
        geocluster_id = body.get('geocluster_id')

        listing_id = data['PostingID']
        listing = self.get_listing_by_id(listing_id)

        try:
            if listing is not None:
                self.update_listing(subdomain, listing, data)
            else:
                listing = self.insert_listing(subdomain, data)

        except KeyError:
            logger.warning("received incomplete listing data", exc_info=True)
            message.ack()
            return

        listing.data = data
        listing.request_token = token
        listing.geocluster_id = geocluster_id

        try:
            within = func.st_within(listing.location.to_wkb(), CensusBlock.geometry)
            census_block = self.session.query(CensusBlock).filter(within).one()
            listing.census_block = census_block
        except NoResultFound:
            logger.warning("ignoring unlocatable listing", extra=dict(listing=data))
            message.ack()
            return

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
        logger.info("updating listing", extra={'listing': data})
        self.copy_json(listing, data)
        listing.subdomain = subdomain

    def insert_listing(self, subdomain, data):
        logger.info("inserting listing", extra={'listing': data})
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
        listing.location = self.parse_location(data['Longitude'],
                                               data['Latitude'])

        return listing

    def parse_location(self, *coords):
        return (map(self.parse_float, coords), self.srid)

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
