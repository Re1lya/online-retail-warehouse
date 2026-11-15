"""新增事实、任意切片及每个 CUBE 层级的独立核算。"""
from decimal import Decimal
import pytest
from src import analytics
from test_analytics import con
from test_model import con as fixture_con, load_boundary_fixture, build_models


def test_cancellation_attributes_and_empty_sales_slice(fixture_con):
    load_boundary_fixture(fixture_con)
    build_models(fixture_con)
    assert fixture_con.execute('SELECT count(*) FROM dwd.fact_sales').fetchone()[0] == 4
    assert fixture_con.execute('SELECT count(*) FROM dwd.fact_cancellation WHERE is_valid_cancellation').fetchone()[0] == 1
    net = analytics.net_overview(fixture_con, '2011-01-01', '2011-01-03')
    assert net['sales_amount'] == Decimal('9.8760')
    assert net['net_recorded_amount'] == Decimal('7.8760')
    assert fixture_con.execute("SELECT observed_country_count FROM dim.customer WHERE customer_id='10001'").fetchone()[0] == 2
    assert fixture_con.execute("SELECT iso_weekday,is_weekend,year_month FROM dim.date WHERE full_date='2011-01-01'").fetchone() == (6,True,'2011-01')
    fixture_con.execute("DELETE FROM stg.clean_transactions WHERE NOT is_cancelled")
    build_models(fixture_con)
    assert analytics.overview(fixture_con,'2011-01-01','2011-01-03')['order_count'] == 0
    assert analytics.net_overview(fixture_con,'2011-01-01','2011-01-03')['net_recorded_amount'] == -2
    assert analytics.net_overview(fixture_con,'2011-01-01','2011-01-03')['cancellation_amount_ratio'] is None


@pytest.mark.parametrize('start,end,selected',[
    ('2010-12-01','2011-12-09',None),
    ('2011-01-05','2011-02-11',['France','Germany']),
    ('2000-01-01','2000-01-02',None),
])
def test_cancel_amount_against_original_source(con,start,end,selected):
    sql = """SELECT -coalesce(sum(try_cast(quantity AS BIGINT)*try_cast(unit_price AS DECIMAL(18,4))),0),
        count(DISTINCT trim(invoice_no)) FROM ods.retail_raw
        WHERE upper(trim(invoice_no)) LIKE 'C%' AND nullif(trim(stock_code),'') IS NOT NULL
        AND try_cast(quantity AS BIGINT)<0 AND try_cast(unit_price AS DECIMAL(18,4))>0
        AND try_cast(invoice_date AS TIMESTAMP)::DATE BETWEEN ? AND ?"""
    params=[start,end]
    if selected:
        sql+=' AND trim(country) IN ('+','.join('?' for _ in selected)+')';params+=selected
    expected=con.execute(sql,params).fetchone()
    actual=analytics.net_overview(con,start,end,selected)
    assert (actual['cancellation_amount'],actual['cancellation_order_count']) == expected
    assert actual['net_recorded_amount']==actual['sales_amount']-actual['cancellation_amount']


@pytest.mark.parametrize('gid',range(8))
def test_all_materialized_cube_levels(con,gid):
    keys=[k for k,mask in [('month_start',4),('country',2),('entry_type',1)] if not gid & mask]
    cols=','.join(keys)
    prefix=cols+',' if cols else ''
    query=f"""SELECT {prefix}sum(line_amount),
        count(DISTINCT invoice_no) FILTER(WHERE entry_type='sale'),
        count(DISTINCT customer_id) FILTER(WHERE entry_type='sale')
        FROM ads.transaction_detail"""
    if cols:query+=' GROUP BY '+cols
    expected=set(con.execute(query).fetchall())
    actual=set(con.execute(f'SELECT {prefix}net_recorded_amount,order_count,customer_count FROM ads.transaction_cube WHERE grouping_id=?',[gid]).fetchall())
    assert actual==expected


@pytest.mark.parametrize('dimensions',[('month',),('country',),('type',),('month','country'),('month','type'),('country','type'),('month','country','type')])
def test_sliced_cube_recomputes_distinct_counts(con,dimensions):
    keys=','.join({'month':'month_start','country':'country','type':'entry_type'}[d] for d in dimensions)
    start,end='2011-01-05','2011-02-11'
    actual=analytics.cube(con,start,end,['France','Germany'],dimensions)
    expected=con.execute(f"""SELECT {keys},sum(line_amount)::DOUBLE AS net_recorded_amount,
        count(DISTINCT invoice_no) FILTER(WHERE entry_type='sale') AS order_count,
        count(DISTINCT customer_id) FILTER(WHERE entry_type='sale') AS customer_count
        FROM ads.transaction_detail WHERE sales_date BETWEEN ? AND ? AND country IN ('France','Germany')
        GROUP BY {keys} ORDER BY {keys}""",[start,end]).fetchdf()
    assert actual.drop(columns=['sales_amount','cancellation_amount']).equals(expected)


def test_rollup_hierarchy(con):
    first,last=analytics.bounds(con)
    rollup=analytics.rollup(con,first,last)
    total=float(analytics.net_overview(con,first,last)['net_recorded_amount'])
    assert set(rollup.grouping_id)=={0,1,3,7}
    for gid in [0,1,3,7]:assert abs(rollup[rollup.grouping_id==gid].net_recorded_amount.sum()-total)<1e-7
