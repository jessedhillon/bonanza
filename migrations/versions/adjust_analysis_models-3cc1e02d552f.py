"""adjust analysis models

Revision ID: 3cc1e02d552f
Revises: 2203590c6b37
Create Date: 2014-11-22 23:25:59.999772

"""

# revision identifiers, used by Alembic.
revision = '3cc1e02d552f'
down_revision = '2203590c6b37'

from alembic import op
import sqlalchemy as sa
import sqlalchemy.sql as sql
from batteries.model.types import Ascii, UTCDateTime
from geoalchemy2 import Geometry


segment = sql.table('segment', sql.column('dimension_id'),
                    sql.column('id'), sql.column('name'),
                    sql.column('numeric_value'), sql.column('string_value'),
                    sql.column('sort_value'))

cb = sql.table('census_block', sql.column('block_ce'),
               sql.column('county_fp'), sql.column('state_fp'),
               sql.column('tract_ce'))

cbs = sql.table('census_block_segment', sql.column('dimension_id'),
                sql.column('id'), sql.column('block_ce'),
                sql.column('county_fp'), sql.column('state_fp'),
                sql.column('tract_ce'))


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('analytic_context',
    sa.Column('key', Ascii(length=40), nullable=False),
    sa.PrimaryKeyConstraint('key', name=op.f('pk_analytic_context'))
    )
    op.create_table('analytic_context_segment',
    sa.Column('analytic_context_key', sa.Unicode(length=40), nullable=False),
    sa.Column('dimension_id', sa.Unicode(length=20), nullable=False),
    sa.Column('segment_id', sa.Unicode(length=20), nullable=False),
    sa.ForeignKeyConstraint(['analytic_context_key'], ['analytic_context.key'], name=op.f('fk_analytic_context_segment_analytic_context_key_series')),
    sa.ForeignKeyConstraint(['dimension_id', 'segment_id'], ['segment.dimension_id', 'segment.id'], name='fk_series_segment'),
    sa.ForeignKeyConstraint(['dimension_id'], ['dimension.id'], name=op.f('fk_analytic_context_segment_dimension_id_dimension')),
    sa.PrimaryKeyConstraint('analytic_context_key', 'dimension_id', 'segment_id', name=op.f('pk_analytic_context_segment'))
    )
    op.create_index('ix_analytic_context_segment', 'analytic_context_segment', ['dimension_id', 'segment_id'], unique=False)
    op.create_index(op.f('ix_analytic_context_segment_analytic_context_key'), 'analytic_context_segment', ['analytic_context_key'], unique=False)
    op.create_table('census_block_segment',
    sa.Column('dimension_id', sa.Unicode(length=20), nullable=False),
    sa.Column('id', sa.Unicode(length=20), nullable=False),
    sa.Column('state_fp', sa.Unicode(length=2), nullable=False),
    sa.Column('county_fp', sa.Unicode(length=3), nullable=False),
    sa.Column('tract_ce', sa.Unicode(length=6), nullable=False),
    sa.Column('block_ce', sa.Unicode(length=1), nullable=False),
    sa.ForeignKeyConstraint(['dimension_id', 'id'], ['segment.dimension_id', 'segment.id'], name=op.f('fk_census_block_segment_dimension_id_segment')),
    sa.ForeignKeyConstraint(['dimension_id'], ['dimension.id'], name=op.f('fk_census_block_segment_dimension_id_dimension')),
    sa.ForeignKeyConstraint(['state_fp', 'county_fp', 'tract_ce', 'block_ce'], ['census_block.state_fp', 'census_block.county_fp', 'census_block.tract_ce', 'census_block.block_ce'], name='fk_craigslist_listing_census_block'),
    sa.PrimaryKeyConstraint('dimension_id', 'id', name=op.f('pk_census_block_segment'))
    )
    op.create_index('ix_census_block_segment_census_block', 'census_block_segment', ['state_fp', 'county_fp', 'tract_ce', 'block_ce'], unique=False)
    op.drop_table('series_segment')
    op.drop_table('census_block_series')
    op.create_index(op.f('ix_craigslist_listing_subdomain'), 'craigslist_listing', ['subdomain'], unique=False)
    op.create_index('ix_homepath_census_block', 'homepath_listing', ['state_fp', 'county_fp', 'tract_ce', 'block_ce'], unique=False)
    op.add_column('series', sa.Column('analytic_context_key', Ascii(length=40), nullable=True))
    op.create_index('ix_series_analytic_context_concept_feature_duration', 'series', ['analytic_context_key', 'concept_id', 'feature_id', 'duration'], unique=False)
    op.alter_column('segment', 'sort_value', type_=sa.Unicode(16))
    ### end Alembic commands ###
    # insert into segment
    #   select 'census_block', concat('cb-', state_fp, county_fp, tract_ce, block_ce),
    #          concat('Census Block ', state_fp, county_fp, tract_ce, block_ce), null,
    #          concat(state_fp, county_fp, tract_ce, block_ce),
    #          concat(state_fp, county_fp, tract_ce, block_ce)
    #   from census_block

    conn = op.get_bind()
    op.execute("""
INSERT INTO segment
    SELECT 'census_block', concat('cb-', state_fp, county_fp, tract_ce, block_ce),
           concat('Census Block ', state_fp, county_fp, tract_ce, block_ce), NULL,
           concat(state_fp, county_fp, tract_ce, block_ce),
           concat(state_fp, county_fp, tract_ce, block_ce)
    FROM census_block""")

    op.execute("""
INSERT INTO census_block_segment
    SELECT 'census_block', concat('cb-', state_fp, county_fp, tract_ce, block_ce),
           state_fp, county_fp, tract_ce, block_ce
    FROM census_block""")


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('series', 'analytic_context_key')
    op.drop_index('ix_homepath_census_block', table_name='homepath_listing')
    op.drop_index(op.f('ix_craigslist_listing_subdomain'), table_name='craigslist_listing')
    op.create_table('census_block_series',
    sa.Column('state_fp', sa.VARCHAR(length=2), autoincrement=False, nullable=False),
    sa.Column('county_fp', sa.VARCHAR(length=3), autoincrement=False, nullable=False),
    sa.Column('tract_ce', sa.VARCHAR(length=6), autoincrement=False, nullable=False),
    sa.Column('block_ce', sa.VARCHAR(length=1), autoincrement=False, nullable=False),
    sa.Column('series_key', sa.VARCHAR(length=40), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['series_key'], [u'series.key'], name=u'fk_census_block_series_series_key_series'),
    sa.ForeignKeyConstraint(['state_fp', 'county_fp', 'tract_ce', 'block_ce'], [u'census_block.state_fp', u'census_block.county_fp', u'census_block.tract_ce', u'census_block.block_ce'], name=u'fk_census_block_series'),
    sa.PrimaryKeyConstraint('state_fp', 'county_fp', 'tract_ce', 'block_ce', 'series_key', name=u'pk_census_block_series')
    )
    op.create_table('series_segment',
    sa.Column('series_key', sa.VARCHAR(length=40), autoincrement=False, nullable=False),
    sa.Column('dimension_id', sa.VARCHAR(length=20), autoincrement=False, nullable=False),
    sa.Column('segment_id', sa.VARCHAR(length=20), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['dimension_id', 'segment_id'], [u'segment.dimension_id', u'segment.id'], name=u'fk_series_segment'),
    sa.ForeignKeyConstraint(['dimension_id'], [u'dimension.id'], name=u'fk_series_segment_dimension_id_dimension'),
    sa.ForeignKeyConstraint(['series_key'], [u'series.key'], name=u'fk_series_segment_series_key_series'),
    sa.PrimaryKeyConstraint('series_key', 'dimension_id', 'segment_id', name=u'pk_series_segment')
    )
    op.drop_index('ix_census_block_segment_census_block', table_name='census_block_segment')
    op.drop_table('census_block_segment')
    op.drop_index(op.f('ix_analytic_context_segment_analytic_context_key'), table_name='analytic_context_segment')
    op.drop_index('ix_analytic_context_segment', table_name='analytic_context_segment')
    op.drop_table('analytic_context_segment')
    op.drop_table('analytic_context')

    op.execute(segment.delete(segment.c.dimension_id == 'census_block'))
    op.alter_column('segment', 'sort_value', type_=sa.Unicode(10))
    ### end Alembic commands ###
