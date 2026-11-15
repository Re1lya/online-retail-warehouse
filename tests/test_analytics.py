"""对真实ODS的独立核算与API结果对照，避免仅测试实现的复述。"""
from datetime import date
from decimal import Decimal
from pathlib import Path
import duckdb
import pytest
from src import analytics

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture(scope="module")
def con():
    path=ROOT/"data/warehouse/retail.duckdb"
    if not path.exists(): pytest.skip("先运行pipeline.py生成真实数据库")
    with duckdb.connect(str(path),read_only=True) as connection:
        yield connection

def baseline(con,start,end,selected):
    sql="""WITH raw AS (
      SELECT trim(invoice_no) AS invoice_no, trim(stock_code) AS stock_code,
        TRY_CAST(invoice_date AS TIMESTAMP)::DATE AS sales_date,
        TRY_CAST(quantity AS BIGINT) AS qty,
        TRY_CAST(unit_price AS DECIMAL(18,4)) AS price,
        NULLIF(trim(customer_id),'') AS customer_id,trim(country) AS country
      FROM ods.retail_raw
    ) SELECT COALESCE(SUM(qty*price),0),COUNT(DISTINCT invoice_no),COALESCE(SUM(qty),0),
        COUNT(DISTINCT customer_id)
      FROM raw WHERE invoice_no IS NOT NULL AND invoice_no<>''
        AND stock_code IS NOT NULL AND stock_code<>'' AND qty>0 AND price>0
        AND upper(invoice_no) NOT LIKE 'C%' AND sales_date BETWEEN ? AND ?"""
    params=[start,end]
    if selected:
        sql+=" AND country IN ("+",".join("?" for _ in selected)+")";params+=selected
    return con.execute(sql,params).fetchone()

@pytest.mark.parametrize("start,end,selected",[
    ("2010-12-01","2011-12-09",None),
    ("2011-03-01","2011-05-31",["United Kingdom"]),
    ("2011-01-01","2011-11-30",["Germany","France"]),
    ("2011-12-09","2011-12-09",None),
    ("2000-01-01","2000-01-02",None),
    ("2010-12-01","2011-12-09",["' OR 1=1 --"]),
])
def test_against_raw(con,start,end,selected):
    expected=baseline(con,start,end,selected)
    actual=analytics.overview(con,start,end,selected)
    assert (actual['sales_amount'],actual['order_count'],actual['units'],actual['customer_count'])==expected
    assert actual['avg_order_value']==(expected[0]/Decimal(expected[1]) if expected[1] else 0)

@pytest.mark.parametrize("grain",["day","month","year"])
def test_rollup_amounts(con,grain):
    start,end=analytics.bounds(con)
    result=analytics.trend(con,start,end,["Germany","France"],grain)
    total=analytics.overview(con,start,end,["Germany","France"])["sales_amount"]
    assert abs(Decimal(str(result.sales_amount.sum()))-total)<Decimal("0.00001")

def test_distinct_customers_are_not_summed(con):
    first,last=analytics.bounds(con)
    global_count=analytics.overview(con,first,last)["customer_count"]
    per_day=con.execute("SELECT SUM(daily_customers) FROM dws.sales_day_country").fetchone()[0]
    assert global_count < per_day

def test_top_products_country_and_customers(con):
    first,last=analytics.bounds(con)
    for country in [None,["Germany"]]:
        products=analytics.products(con,first,last,country)
        assert len(products)<=10 and products.sales_amount.is_monotonic_decreasing
        customers=analytics.customers(con,first,last,country)
        assert customers.customer_id.notna().all() and customers.sales_amount.is_monotonic_decreasing
    assert analytics.countries(con)==sorted(analytics.countries(con))

def test_invalid_parameters(con):
    with pytest.raises(ValueError):analytics.overview(con,"2011-12-01","2010-01-01")
    with pytest.raises(ValueError):analytics.trend(con,"2011-01-01","2011-02-01",grain="unsupported")
