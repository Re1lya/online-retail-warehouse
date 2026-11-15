"""看板和离线报告共用的指标接口。所有查询参数化，金额底层使用DECIMAL。"""
from datetime import date
from decimal import Decimal


def bounds(con):
    return con.execute("SELECT MIN(sales_date), MAX(sales_date) FROM ads.sales_detail").fetchone()


def countries(con):
    return [r[0] for r in con.execute("SELECT DISTINCT country FROM ads.sales_detail ORDER BY country").fetchall()]


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
