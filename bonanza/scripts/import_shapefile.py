"""Populate bonanza database

Usage:
    import_shapefile <family> <shapefile> [--config=<config>]

Options:
    -c <config>, --config=<config>      The path to the configuration file, [default: ./bonanza.ini]
"""

import sys
import logging
import transaction

from docopt import docopt
import fiona
from shapely.geometry import shape, Polygon, MultiPolygon

import bonanza.scripts.common as common
from bonanza.models.base import CensusBlock
import bonanza.models as models


logger = logging.getLogger(__name__)


def main(argv=sys.argv):
    try:
        settings = None
        arguments = docopt(__doc__)
        config_uri = arguments['--config']
        settings = common.configure(config_uri)

        import_shapefile(arguments, settings)

    except Exception:
        if settings is None:
            settings = dict({
                'bonanza.debug': False,
            })
        common.post_mortem(settings)


def import_shapefile(arguments, settings):
    if arguments['<family>'] != 'block':
        raise ValueError("Unsupported: {}".format(arguments['<family>']))

    logger.debug("opening {}".format(arguments['<shapefile>']))

    shapefile = fiona.open(arguments['<shapefile>'])
    for i, s in shapefile.items():
        poly = shape(s['geometry'])

        p = s['properties']
        statefp = p['STATEFP']
        countyfp = p['COUNTYFP']
        tractce = p['TRACTCE']
        blkgrpce = p['BLKGRPCE']

        block = CensusBlock.get(statefp, countyfp, tractce, blkgrpce)
        if not block:
            block = CensusBlock(state_fp=statefp, county_fp=countyfp,
                                tract_ce=tractce, block_ce=blkgrpce)
            if isinstance(poly, Polygon):
                block.geometry = MultiPolygon([poly])
            else:
                block.geometry = poly

            logger.debug("{:5d}/{:5d} - adding block {}"
                         .format(i + 1, len(shapefile), block.geo_id))
            models.session.add(block)
        else:
            logger.debug("{:5d}/{:5d} - skipping"
                         .format(i + 1, len(shapefile)))

    models.session.commit()
