# bonanza Description

Data experiments in real estate

## Installation

1. `git clone` the repo to your local filesystem. 
1. Create a virtualenv: `mkvirtualenv bonanza`
1. Install the dependencies: `$ python setup.py develop`
1. Now you're ready to configure Postgres and run the migrations

### PostGIS and Alembic

#### Ubuntu

    $ sudo aptitude install postgresql
    $ sudo aptitude install postgresql-9.3-postgis-2.1` or latest version

#### Mac

* [Postgres.app](http://postgresapp.com/)
* `homebrew install postgis`

#### Create database

```
$ sudo su - postrgres
$ createuser bonanza
$ createdb -O bonanza bonanza
$ psql bonanza
bonanza# create extension postgis;
bonanza# create extension postgis_topology;
bonanza# create extension fuzzystrmatch;
bonanza# create extension postgis_tiger_decoder;
```

#### Run migrations

`cd` to the bonanza project directory (same directory as `development.ini`) Make sure you're working from the `bonanza` virtualenv: `workon bonanza`

Next, run the alembic migrations: 

             $ cd ~/Projects/bonanza
             $ workon bonanza
    (bonanza)$ alembic -c development.ini upgrade head
