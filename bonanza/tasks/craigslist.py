from urlparse import urlunsplit
import requests
from celery import Task
import logging


logger = logging.getLogger(__name__)


class JsonSearchTask(Task):
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux i686) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/37.0.2062.120 Safari/537.36',
    }

    def run(self, region, endpoint, name, state):
        self.subdomain = region
        self.endpoint = endpoint

        logging.info("fetching {}".format(self.url))
        r = requests.get(self.url, headers=self.headers)

        for l in r.json()[0]:
            if 'GeoCluster' in l:
                ExpandGeoClusterListingTask().delay(l)
            else:
                SaveListingTask().delay(l)

    @property
    def url(self):
        return urlunsplit((
            "http",
            "{}.craigslist.org".format(self.subdomain),
            self.endpoint,
            "", ""
        ))


class SaveListingTask(Task):
    def run(self, data):
        import pdb; pdb.set_trace()


class ExpandGeoClusterListingTask(Task):
    def run(self, data):
        import pdb; pdb.set_trace()
