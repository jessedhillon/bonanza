from dateutil.tz import tzutc
from datetime import datetime, date, timedelta
from socket import timeout
import logging

from sqlalchemy.orm.exc import NoResultFound

from bonanza.models.base import CraigslistListing, CensusBlock, Dimension,\
    Segment, Feature, Concept, Series, AnalyticContext
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
        d = date.today()
        rental_query = self.session.query(CensusBlock)

        count = rental_query.count()
        logger.info("enqueueing {} blocks with rental listings".format(count))

        with self.get_producer() as producer:
            offset = 0
            while offset < count:
                for b in rental_query.limit(500).offset(offset):
                    if self.is_stopped:
                        return
                    self.produce_craigslist_block(b, d, producer)
                offset += 500

    def produce_craigslist_block(self, block, date, producer):
        threshold = date - timedelta(days=self.threshold)

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
            'date': date.strftime("%Y-%m-%d"),
            'census_block': (block.state_fp, block.county_fp, block.tract_ce,
                             block.block_ce),
            'listings': [l.key for l in block.craigslist_listings
                         if threshold < l.ctime.date() <= date]
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
        d = datetime.strptime(body['date'], "%Y-%m-%d").date()

        bedrooms = self.session.query(Dimension).get('bedrooms')
        median = self.session.query(Concept).get('median')
        rent_ask = self.session.query(Feature).get('rent-ask')

        if body['listing_type'] == 'rental' and body['source'] == 'craigslist':
            if body['listings']:
                listings = self.session.query(CraigslistListing)\
                                       .filter(CraigslistListing.key.in_(body['listings']))\
                                       .all()
            else:
                listings = []

        logging.debug("processing {} listings for {}".format(len(listings), block.geo_id))

        for segment in bedrooms.segments:
            logging.debug("{} - {} {}".format(block.geo_id, segment.dimension.name, segment.name))
            context = self.get_context_for(block.segment, segment)

            for duration in [1, 7, 14, 28]:
                series = self.get_series_for(context, median, rent_ask, duration)
                interesting = self.filter_listings(listings, d, duration)
                features = self.extract_features(interesting, segment, rent_ask)
                v = median.compute(features)
                series.measures[d] = v
                if v > 0.0:
                    logger.info("{!r} adding fact [{}] {} {} {} days -> {}"
                                .format(context, d, rent_ask.name, median.name, duration, v))
                self.session.add(series)

        self.session.commit()
        message.ack()

    def get_context_for(self, *segments):
        try:
            q = self.session.query(AnalyticContext)
            for s in segments:
                q = q.filter(AnalyticContext.segments.any(Segment.id == s.id))

            return q.one()
        except NoResultFound:
            ctx = AnalyticContext()
            ctx.segments.extend(segments)
            self.session.add(ctx)
            return ctx

    def get_series_for(self, context, concept, feature, duration):
        try:
            return self.session.query(Series)\
                       .filter(Series.analytic_context_key == context.key)\
                       .filter(Series.concept_id == concept.id)\
                       .filter(Series.feature_id == feature.id)\
                       .filter(Series.duration == duration)\
                       .one()
        except NoResultFound:
            s = Series(analytic_context=context, concept=concept,
                       feature=feature, duration=duration)
            self.session.add(s)
            return s

    @staticmethod
    def filter_listings(listings, date, duration):
        threshold = date - timedelta(days=duration)
        return [l for l in listings if threshold < l.ctime.date() <= date]

    def extract_features(self, listings, segment, feature):
        return [feature.extract_feature(l) for l in listings if l in segment]
