import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
readme = open(os.path.join(here, 'README.md')).read()
changes = open(os.path.join(here, 'CHANGES.rst')).read()

requires = [
    'alembic',
    'docopt',
    'geoalchemy2',
    'librabbitmq',
    'kombu',
    'paster',
    'psycopg2',
    'pyquery',
    'pyramid==1.5.1',
    'pyramid_beaker',
    'pyramid_debugtoolbar',
    'pyramid_jinja2',
    'pyramid_scss',
    'pyramid_tm',
    'python-dateutil<2.0',
    'raven',
    'requests==2.4.1',
    'SQLAlchemy==0.9.7',
    'sqlalchemy-batteries>=0.4.2',
    'transaction',
    'waitress',
    'zope.sqlalchemy',
]

setup(
    name='bonanza',
    version='0.0',
    description='bonanza',
    long_description="{}\n\n{}".format(readme, changes),
    classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
    ],
    author='',
    author_email='',
    url='',
    keywords='web wsgi bfg pylons pyramid',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    test_suite='bonanza',
    install_requires=requires,
    entry_points={
        'paste.app_factory': [
            'main = bonanza:main',
        ],
        'console_scripts': [
            'populate_bonanza = bonanza.scripts.populate:main',
            'task = bonanza.scripts.task:main',
            'consumer = bonanza.scripts.consumer:main',
            'producer = bonanza.scripts.producer:main',
        ]
    },
)
