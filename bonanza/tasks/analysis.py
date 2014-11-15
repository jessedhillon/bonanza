from dateutil.tz import tzutc
from datetime import datetime, date, timedelta
from socket import timeout
import logging

import numpy
from sqlalchemy import func

from bonanza.models.base import CraigslistListing, HomepathListing, CensusBlock,\
    Dimension, Series, Feature, Concept
from bonanza.tasks import Task
import bonanza.models as models
import bonanza.tasks.common as common


logger = logging.getLogger(__name__)


class AnalysisProducerTask(Task):
    run_once = False
    threshold = 30

    def __init__(self, *args, **kwargs):
        super(AnalysisProducerTask, self).__init__(*args, **kwargs)
        self.sql = models.engine.connect()
        self.session = models.Session(bind=self.sql)

    def run(self):
        try:
            while True:
                if not self.run_once:
                    self.sleep_until(self.next_occurrence)

                if self.is_stopped:
                    return

                self.process_blocks()
                if self.run_once:
                    self.stop()
        except:
            common.post_mortem()

    def process_blocks(self):
        threshold = date.today() - timedelta(days=self.threshold)
        threshold = datetime.combine(threshold, datetime.min).replace(tzinfo=tzutc())
        rental_blocks = self.session.query(CensusBlock)\
                                    .join(CraigslistListing)\
                                    .filter(CraigslistListing.ctime >= threshold)\
                                    .group_by(CensusBlock.state_fp, CensusBlock.county_fp,
                                              CensusBlock.tract_ce, CensusBlock.block_ce)\
                                    .having(func.count(CraigslistListing.key) > 0)

        homepath_blocks = self.session.query(CensusBlock)\
                                      .join(HomepathListing)\
                                      .group_by(CensusBlock.state_fp, CensusBlock.county_fp,
                                                CensusBlock.tract_ce, CensusBlock.block_ce)\
                                      .having(func.count(HomepathListing.key) > 0)

        with self.get_producer() as producer:
            for b in rental_blocks:
                if self.is_stopped:
                    break
                self.produce_craigslist_block(b, producer)

            for b in homepath_blocks:
                if self.is_stopped:
                    break
                self.produce_homepath_block(b, producer)

    def produce_craigslist_block(self, block, producer):
        extra = {
            'state_fp': block.state_fp,
            'county_fp': block.county_fp,
            'tract_ce': block.tract_ce,
            'block_ce': block.block_ce,
        }
        logger.info("enqueueing rental block", extra=extra)

        data = {
            'listing_type': 'rental',
            'source': 'craigslist',
            'census_block': (block.state_fp, block.county_fp, block.tract_ce,
                             block.block_ce),
            'listings': [l.key for l in block.craigslist_listings]
        }
        producer.publish(
            data,
            exchange=self.get_exchange('analysis'),
            routing_key='analysis.census_blocks.rental',
            declare=[self.get_queue('analysis_blocks')])

    def produce_homepath_block(self, block, producer):
        extra = {
            'state_fp': block.state_fp,
            'county_fp': block.county_fp,
            'tract_ce': block.tract_ce,
            'block_ce': block.block_ce,
        }
        logger.info("enqueueing sale[distressed] block", extra=extra)

        data = {
            'listing_type': 'sale',
            'source': 'homepath',
            'census_block': (block.state_fp, block.county_fp, block.tract_ce,
                             block.block_ce),
            'listings': [l.key for l in block.homepath_listings]
        }
        producer.publish(
            data,
            exchange=self.get_exchange('analysis'),
            routing_key='analysis.census_blocks.sale',
            declare=[self.get_queue('analysis_blocks')])


class CensusBlockAnalysisTask(Task):
    def __init__(self, *args, **kwargs):
        super(CensusBlockAnalysisTask, self).__init__(*args, **kwargs)
        self.sql = models.engine.connect()
        self.session = models.Session(bind=self.sql)

    def run(self):
        try:
            with self.get_consumer('analysis_blocks'):
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
        block = self.session.query(CensusBlock).get(body['census_block'])
        today = date.today()

        dimensions = [self.session.query(Dimension).get('bedrooms')]
        median = self.session.query(Concept).get('median')
        rent_ask = self.session.query(Feature).get('rent-ask')

        if body['listing_type'] == 'rental' and body['source'] == 'craigslist':
            listings = self.session.query(CraigslistListing)\
                                   .filter(CraigslistListing.key.in_(body['listings']))\
                                   .all()

            logger.info("processing rental listings for census block")
            for duration in [1, 7, 14, 28]:
                fact_date = today - timedelta(days=duration)
                listings = [l for l in listings if fact_date <= l.ctime.date() <= today]

                for d in dimensions:
                    by_segments = self.listings_by_segments(d, listings)

                    for concept, feature in [(median, rent_ask)]:
                        for segment, listings in by_segments.items():
                            series = self.get_series_for_block(block, concept, feature,
                                                               duration, [segment])
                            if not series:
                                series = Series(concept=concept, feature=feature,
                                                duration=duration, segments=[segment])
                                block.series.append(series)

                            v = self._compute_concept(listings, concept, feature)
                            series.measures[fact_date] = v
                            self.session.add(series)

        self.session.commit()
        message.ack()

    @staticmethod
    def listings_by_segments(dimension, listings):
        if dimension.id == 'bedrooms':
            segments = {s.value: s for s in dimension.segments}
            by_bedrooms = {s: [] for s in dimension.segments}
            for l in listings:
                beds = CensusBlockAnalysisTask._get_bedrooms(l)
                if beds < 5:
                    segment = segments.get(beds)
                else:
                    segment = segments.get('5+')
                by_bedrooms.setdefault(segment).append(l)
            return by_bedrooms

    @staticmethod
    def _get_bedrooms(listing):
        if isinstance(listing, CraigslistListing):
            return listing.bedrooms
        elif isinstance(listing, HomepathListing):
            return listing.beds

    @staticmethod
    def _compute_concept(listings, concept, feature, default=0):
        if len(listings) == 0:
            return default

        if concept.id == 'median':
            op = numpy.median
        elif concept.id == 'mean':
            op = numpy.mean
        features = [CensusBlockAnalysisTask._get_feature(l, feature) for l in listings]
        return op(features)

    @staticmethod
    def _get_feature(listing, feature):
        if isinstance(listing, CraigslistListing):
            if feature.id == 'rent-ask':
                return listing.ask

    def get_series_for_block(self, block, concept, feature, duration, segments):
        for series in block.series:
            if series.concept == concept and series.feature == feature\
                    and series.duration == duration:
                if set(segments) == set(series.segments):
                    return series
