import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
readme = open(os.path.join(here, 'README.md')).read()
changes = open(os.path.join(here, 'CHANGES.rst')).read()

requires = [
    'paster',
    'requests',
    'pyquery',
    'celery[librabbitmq]',
    'psycopg2',
    'pyramid',
    'SQLAlchemy',
    'transaction',
    'pyramid_tm',
    'pyramid_debugtoolbar',
    'pyramid_beaker',
    'pyramid_scss',
    'pyramid_jinja2',
    'zope.sqlalchemy',
    'waitress',
    'python-dateutil<2.0',
    'sqlalchemy-batteries',
    'docopt',
    'alembic',
    'geoalchemy2',
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
            'consumer = bonanza.scripts.consumer:main',
            'producer = bonanza.scripts.producer:main',
        ]
    },
)
