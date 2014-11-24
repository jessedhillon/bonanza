"""Populate bonanza database fixtures

Usage:
    populate_bonanza [--config=<config>]
    populate_bonanza (-h | --help)

Options:
    -c <config>, --config=<config>      The path to the configuration file,
                                        [default: ./bonanza.ini]
"""

import sys
import logging

from docopt import docopt

import bonanza.models as models
import bonanza.scripts.common as common
from bonanza.models.base import Concept, Feature, Dimension, Segment, CensusBlock,\
    CensusBlockSegment

logger = None

# warnings.filterwarnings('error')


def main(argv=sys.argv):
    global logger

    try:
        settings = None
        arguments = docopt(__doc__)
        config_uri = arguments['--config']
        settings = common.configure(config_uri)

        logger = logging.getLogger(__name__)
        populate(arguments, settings)

    except Exception:
        if settings is None:
            settings = dict({
                'bonanza.debug': True,
            })
        common.post_mortem(settings)


def populate(arguments, settings):
    concepts = [{
        'id': u'mean',
        'name': u"Mean"
    }, {
        'id': u'median',
        'name': u"Median"
    }]

    features = [{
        'id': u'rent-ask',
        'name': u"Advertised Rental Price",
    }]

    dimensions = [{
        'id': u'census_block',
        'name': u"Census Block",
        'segments': []
    }, {
        'id': u'bedrooms',
        'name': u"Number of Bedrooms",
        'segments': [{
            'id': 'all',
            'name': 'Any',
            'sort_value': 0,
        }, {
            'id': '1',
            'name': '1',
            'value': 1,
            'sort_value': 1,
        }, {
            'id': '2',
            'name': '2',
            'value': 2,
            'sort_value': 2,
        }, {
            'id': '3',
            'name': '3',
            'value': 3,
            'sort_value': 3,
        }, {
            'id': '4',
            'name': '4',
            'value': 4,
            'sort_value': 4,
        }, {
            'id': '5+',
            'name': '5 or more',
            'value': '5+',
            'sort_value': 5,
        }]
    }, {
        'id': u'bathrooms',
        'name': u"Number of Bathrooms",
        'segments': [{
            'id': 'all',
            'name': 'Any',
            'sort_value': 0,
        }, {
            'id': '1',
            'name': '1',
            'value': 1,
            'sort_value': 1,
        }, {
            'id': '2',
            'name': '2',
            'value': 2,
            'sort_value': 2,
        }, {
            'id': '3',
            'name': '3',
            'value': 3,
            'sort_value': 3,
        }, {
            'id': '4',
            'name': '4',
            'value': 4,
            'sort_value': 4,
        }, {
            'id': '5+',
            'name': '5 or more',
            'value': '5+',
            'sort_value': 5,
        }]
    }]

    for c in concepts:
        if Concept.get(c['id']):
            continue

        logger.info("inserting concept {id}".format(**c))
        models.session.add(Concept(**c))

    for f in features:
        if Feature.get(f['id']):
            continue

        logger.info("inserting feature {id}".format(**f))
        models.session.add(Feature(**f))

    for d in dimensions:
        segments = d.pop('segments', [])
        dimension = Dimension.get(d['id']) or Dimension(**d)
        logger.info("inserting dimension {id}".format(**d))

        for s in segments:
            segment = Segment.get(d['id'], s['id']) or Segment(**s)
            logger.info("inserting segment {}/{}".format(d['id'], s['id']))
            dimension.segments.append(segment)

        models.session.add(dimension)

    models.session.commit()
