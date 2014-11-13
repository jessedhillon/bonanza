from datetime import datetime
from requests.exceptions import ConnectionError, HTTPError, ConnectTimeout
from socket import timeout
from uuid import uuid4 as uuid
import base64
import logging
import random
import re
import requests

from sqlalchemy import func
from sqlalchemy.orm.exc import NoResultFound

from bonanza.models.base import HomepathListing, CensusBlock
from bonanza.tasks import Task
import bonanza.models as models
import bonanza.tasks.common as common
from pyquery import PyQuery


logger = logging.getLogger(__name__)


class UrlProducerTask(Task):
    run_once = False
    states = ('AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
              'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
              'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
              'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
              'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY')

    def run(self):
        try:
            while True:
                if not self.run_once:
                    self.sleep_until(self.next_occurrence)

                if self.is_stopped:
                    return

                self.enqueue_searches()
                if self.run_once:
                    self.stop()

        except:
            common.post_mortem()

    def enqueue_searches(self):
        with self.get_producer() as producer:
            states = list(self.states)
            random.shuffle(states)
            for abbrev in states:
                logger.info("beginning result chain", extra=dict(state=abbrev))
                data = {
                    'state': abbrev,
                    'page': 1,
                }
                producer.publish(
                    data,
                    exchange=self.get_exchange('requests'),
                    routing_key='requests.homepath.results',
                    declare=[self.get_queue('requests')])


class JsonSearchTask(Task):
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux i686) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/37.0.2062.120 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest'
    }

    def generate_request_token(self):
        return uuid().bytes

    def generate_params(self, state, page):
        params = {
            'q': state,
            'pg': page,
            'fragments': 'filters,header,results,footer',
        }

        params.update({k: '' for k in ('pi', 'pa', 'bdi', 'bhi', 'ms', 'xs',
                                       'ptany', 'srcstany', 'otherAny', 'ob',
                                       'st', 'cno', 'o', 'boundingTopLeft',
                                       'boundingBottomRight', 'ci', 'ps')})

        return params

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

    def receive(self, body, message):
        url = "https://www.homepath.com/listing/search/ui/event"
        params = self.generate_params(body['state'], body['page'])

        try:
            self.acquire_token()
            token = base64.b64encode(self.generate_request_token())

            r = requests.get(url, params=params, headers=self.headers)
            logger.debug("requesting {state}[{page}]".format(**body))

            try:
                j = r.json()
                results = j['results']
            except ValueError:
                logger.exception("json decode error")
                message.requeue()
                return

            extra = {
                'token': token,
                'request': body,
            }
            extra.update({k: j.get(k) for k in ('stateCode', 'totalCount',
                                                'currentPageNumber', 'query',
                                                'numberOfPages', 'status',
                                                'previousPageNumber',
                                                'nextPageNumber')})
            logger.info("processing results", extra=extra)

            for l in results:
                with self.get_producer() as producer:
                    extra = {
                        'token': token,
                        'request': body,
                        'listing': l,
                    }
                    if not l['price']:
                        logger.warn("ignoring non-priced listing", extra=extra)
                        continue

                    if not l['lat'] or not l['lng']:
                        logger.warn("ignoring non-geocoded listing",
                                    extra=extra)
                        continue

                    data = {
                        '_token': token,
                        'data': l,
                        'fragment': self.extract_fragment(l, j['fragments'])
                    }
                    producer.publish(
                        data,
                        exchange=self.get_exchange('listings'),
                        routing_key='listings.homepath',
                        declare=[self.get_exchange('listings'),
                                 self.get_queue('listings')])

            if j['currentPageNumber'] < j['numberOfPages']:
                with self.get_producer() as producer:
                    data = {
                        'state': body['state'],
                        'page': body['page'] + 1
                    }
                    producer.publish(
                        data,
                        exchange=self.get_exchange('requests'),
                        routing_key='requests.homepath.results',
                        declare=[self.get_exchange('requests')])

            message.ack()

        except (HTTPError, ConnectionError, ConnectTimeout):
            logger.exception("request exception")
            message.requeue()

    @staticmethod
    def extract_fragment(listing, fragments):
        pq = PyQuery(fragments['results'])
        selector = 'tr a.address[href$="{listingId}"]'.format(**listing)
        return pq.find(selector).closest('tr').outerHtml()


class ListingProcessorTask(Task):
    srid = 4326
    price_pattern = re.compile(r'[\$,\.]')

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
        fragment = body['fragment']
        token = base64.b64decode(body['_token']) if '_token' in body else None

        listing_id = data['listingId']
        listing = self.get_listing_by_id(listing_id)

        try:
            if listing is not None:
                self.update_listing(listing, data, fragment)
            else:
                listing = self.insert_listing(data, fragment)
        except (ValueError, TypeError, KeyError):
            extra = {
                'token': token,
                'listing': data
            }
            logger.exception("unable to parse listing", extra=extra)
            message.ack()
            return

        data['_fragment'] = fragment
        listing.data = data
        listing.request_token = token

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
            return self.session.query(HomepathListing).\
                filter_by(id=unicode(listing_id)).one()
        except NoResultFound:
            return None

    def update_listing(self, listing, data, fragment):
        logger.info("updating listing", extra={'listing': data})
        self.copy_json(listing, data, fragment)

    def insert_listing(self, data, fragment):
        logger.info("inserting listing", extra={'listing': data})
        listing = HomepathListing()
        self.copy_json(listing, data, fragment)
        return listing

    def copy_json(self, listing, data, fragment):
        listing.id = data['listingId']
        listing.baths = self.parse_int(data['baths'])
        listing.beds = self.parse_int(data['beds'])
        listing.status = self.parse_status(data['status'], fragment)
        listing.price = self.parse_price(data['price'])
        listing.image_url = self.parse_image_url(fragment)
        listing.location = self.parse_location(data['lng'], data['lat'])
        listing.entry_date = self.parse_date(data['entryDate'])
        listing.property_type = data['propertyType']
        listing.street = data['street']
        listing.city = data['city']
        listing.state = data['state']

        return listing

    @staticmethod
    def make_image_url(listing):
        fmt = "homepathlistingphoto.html?"\
              "s={listingIdSimpleEnc!s}&"\
              "d={addressIdSimpleEnc}&"\
              "pse={photoIdSimpleEnc}"
        return fmt.format(**listing)

    def parse_status(self, status, fragment):
        if status != 'active':
            return status

        return PyQuery(fragment).find('td').eq(5).text().lower()

    def parse_image_url(self, fragment):
        return PyQuery(fragment).find('td').eq(0).find('img').attr('src')

    def parse_price(self, v):
        return int(self.price_pattern.sub('', v))

    def parse_location(self, *coords):
        return (map(self.parse_float, coords), self.srid)

    def parse_date(self, v):
        return datetime.fromtimestamp(int(v)/1000).date()

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
