"""看板和离线报告共用的指标接口。所有查询参数化，金额底层使用DECIMAL。"""
from datetime import date
from decimal import Decimal


def bounds(con):
    return con.execute("SELECT MIN(sales_date), MAX(sales_date) FROM ads.transaction_detail").fetchone()


def countries(con):
    return [r[0] for r in con.execute("SELECT DISTINCT country FROM ads.transaction_detail ORDER BY country").fetchall()]


def _filters(start, end, selected):
    start = date.fromisoformat(str(start)[:10])
    end = date.fromisoformat(str(end)[:10])
    if start > end:
        raise ValueError("开始日期不能晚于结束日期")
    where = "sales_date BETWEEN ? AND ?"
    params = [start, end]
    if selected:
        where += " AND country IN (" + ",".join("?" for _ in selected) + ")"
        params.extend(selected)
    return where, params


def overview(con, start, end, countries=None):
    where, params = _filters(start, end, countries)
    amount, units = con.execute(
        f"SELECT COALESCE(SUM(sales_amount),0), COALESCE(SUM(units),0) FROM ads.sales_daily WHERE {where}", params
    ).fetchone()
    orders, customers = con.execute(
        f"SELECT COUNT(DISTINCT invoice_no), COUNT(DISTINCT CASE WHEN customer_key<>0 THEN customer_id END) FROM ads.sales_detail WHERE {where}", params
    ).fetchone()
    return dict(sales_amount=amount, order_count=orders, units=int(units),
                customer_count=customers, avg_order_value=amount / Decimal(orders) if orders else Decimal(0))


def trend(con, start, end, countries=None, grain="month"):
    if grain not in {"day", "month", "year"}:
        raise ValueError("时间粒度只能是day/month/year")
    where, params = _filters(start, end, countries)
    # 销售额从汇总层上卷，订单数按同一周期在明细中重新去重。
    return con.execute(f"""
        WITH amounts AS (
          SELECT DATE_TRUNC('{grain}',sales_date)::DATE AS period, SUM(sales_amount) AS sales_amount
          FROM ads.sales_daily WHERE {where} GROUP BY 1
        ), orders AS (
          SELECT DATE_TRUNC('{grain}',sales_date)::DATE AS period, COUNT(DISTINCT invoice_no) AS order_count
          FROM ads.sales_detail WHERE {where} GROUP BY 1
        ) SELECT * FROM amounts JOIN orders USING(period) ORDER BY period
    """, params + params).fetchdf()


def products(con, start, end, countries=None, limit=10):
    where, params = _filters(start, end, countries)
    return con.execute(f"""SELECT stock_code, description, SUM(sales_amount) AS sales_amount,
      SUM(units)::BIGINT AS units FROM ads.product_daily WHERE {where}
      GROUP BY stock_code, description ORDER BY sales_amount DESC, stock_code LIMIT ?""",
      params + [max(1,min(int(limit),1000))]).fetchdf()


def country_ranking(con, start, end, countries=None):
    where, params = _filters(start, end, countries)
    return con.execute(f"""WITH totals AS (
      SELECT country,SUM(sales_amount) AS sales_amount FROM ads.sales_daily WHERE {where} GROUP BY country
    ), orders AS (
      SELECT country,COUNT(DISTINCT invoice_no) AS order_count FROM ads.sales_detail WHERE {where} GROUP BY country
    ) SELECT * FROM totals JOIN orders USING(country) ORDER BY sales_amount DESC, country""", params+params).fetchdf()


def customers(con, start, end, countries=None, limit=10):
    where, params = _filters(start, end, countries)
    return con.execute(f"""WITH totals AS (
      SELECT customer_id,SUM(sales_amount) AS sales_amount FROM ads.customer_daily WHERE {where} GROUP BY customer_id
    ), orders AS (
      SELECT customer_id,COUNT(DISTINCT invoice_no) AS order_count FROM ads.sales_detail
      WHERE {where} AND customer_key<>0 GROUP BY customer_id
    ) SELECT * FROM totals JOIN orders USING(customer_id)
      ORDER BY sales_amount DESC,customer_id LIMIT ?""",params+params+[max(1,min(int(limit),1000))]).fetchdf()


def net_overview(con, start, end, countries=None):
    where, params = _filters(start, end, countries)
    sale, cancelled, net, cancelled_orders = con.execute(f"""
        SELECT COALESCE(SUM(line_amount) FILTER(WHERE entry_type='sale'),0),
          -COALESCE(SUM(line_amount) FILTER(WHERE entry_type='cancellation'),0),
          COALESCE(SUM(line_amount),0),
          COUNT(DISTINCT invoice_no) FILTER(WHERE entry_type='cancellation')
        FROM ads.transaction_detail WHERE {where}
    """, params).fetchone()
    return dict(sales_amount=sale,cancellation_amount=cancelled,net_recorded_amount=net,
                cancellation_order_count=cancelled_orders,
                cancellation_amount_ratio=cancelled/sale if sale else None)


def net_trend(con, start, end, countries=None, grain='month'):
    if grain not in {'day','month','year'}: raise ValueError('时间粒度无效')
    where, params = _filters(start,end,countries)
    return con.execute(f"""SELECT date_trunc('{grain}',sales_date)::DATE AS period,
        SUM(sales_amount) AS sales_amount,SUM(cancellation_amount) AS cancellation_amount,
        SUM(net_recorded_amount) AS net_recorded_amount
        FROM ads.net_daily WHERE {where} GROUP BY 1 ORDER BY 1""",params).fetchdf()


def cube(con, start, end, countries=None, dimensions=('month','country')):
    """精确日期切片后重新计算立方体，只返回一个汇总层级，禁止跨层重复相加。"""
    allowed={'month':'month_start','country':'country','type':'entry_type'}
    if not dimensions or len(set(dimensions))!=len(dimensions) or not set(dimensions)<=allowed.keys():
        raise ValueError('汇总维度无效')
    where,params=_filters(start,end,countries)
    fields=','.join(allowed[x] for x in dimensions)
    gid=(0 if 'month' in dimensions else 4)+(0 if 'country' in dimensions else 2)+(0 if 'type' in dimensions else 1)
    first,last=bounds(con)
    if params[:2]==[first,last] and (not countries or 'country' in dimensions):
        restriction='grouping_id=?'
        cube_params=[gid]
        if countries:
            restriction+=' AND country IN ('+','.join('?' for _ in countries)+')'
            cube_params+=list(countries)
        return con.execute(f'''SELECT {fields},sales_amount,cancellation_amount,net_recorded_amount,
            order_count,customer_count FROM ads.transaction_cube WHERE {restriction} ORDER BY {fields}''',cube_params).fetchdf()
    # CUBE在过滤后的明细上重新计算，因此任意日期区间的订单和客户去重数仍正确。
    return con.execute(f"""WITH sliced AS (SELECT * FROM ads.transaction_detail WHERE {where}),
      cube AS (SELECT month_start,country,entry_type,
        grouping_id(month_start,country,entry_type) AS grouping_id,
        COALESCE(SUM(line_amount) FILTER(WHERE entry_type='sale'),0) AS sales_amount,
        -COALESCE(SUM(line_amount) FILTER(WHERE entry_type='cancellation'),0) AS cancellation_amount,
        SUM(line_amount) AS net_recorded_amount,
        COUNT(DISTINCT invoice_no) FILTER(WHERE entry_type='sale') AS order_count,
        COUNT(DISTINCT customer_id) FILTER(WHERE entry_type='sale') AS customer_count
      FROM sliced GROUP BY CUBE(month_start,country,entry_type))
      SELECT {fields},sales_amount,cancellation_amount,net_recorded_amount,order_count,customer_count
      FROM cube WHERE grouping_id=? ORDER BY {fields}""",params+[gid]).fetchdf()


def rollup(con,start,end,countries=None):
    where,params=_filters(start,end,countries)
    return con.execute(f"""SELECT year,quarter,month,
      grouping_id(year,quarter,month)::INTEGER AS grouping_id,
      SUM(line_amount) AS net_recorded_amount
      FROM ads.transaction_detail WHERE {where}
      GROUP BY ROLLUP(year,quarter,month) ORDER BY year NULLS LAST,quarter NULLS LAST,month NULLS LAST""",params).fetchdf()
