import requests
from urlparse import urlparse, urlsplit, urlunsplit
from pyquery import PyQuery


states = [
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'HI', 'ID',
    'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS',
    'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK',
    'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV',
    'WI', 'WY',
]

urls = {}


def discover_endpoint(urlbase):
    base = urlsplit(urlbase)
    url = urlunsplit((base.scheme, base.netloc, "/jsonsearch/apa", "", ""))
    r = requests.get(url)

    if r.status_code == 200:
        return "/jsonsearch/apa"

    return "/jsonsearch/aap"

for abbrev in states:
    state_url = "http://geo.craiglist.org/iso/us/{}".format(abbrev.lower())
    print "fetching", abbrev

    r = requests.get(state_url)
    pq = PyQuery(r.content)
    links = []

    if r.history[-1].status_code == 302:
        print "encountered HTTP 302"
        links.append((r.history[-1].headers['location'],
                      pq.find('#topban h2').text()))

    else:
        links.extend((a.attrib['href'],
                      a.text_content()) for a in pq.find('#list a'))

    for url, name in links:
        print "processing", name
        urls.setdefault(abbrev, []).append({
            'region': urlparse(url).netloc.split('.')[0],
            'name': name,
            'endpoint': discover_endpoint(url),
            'state': abbrev,
        })

import pdb; pdb.set_trace()
