"""真实数仓上的界面集成测试，直接SQL校核筛选后的KPI。"""
from datetime import date
from decimal import Decimal
from pathlib import Path

import duckdb
import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "data/warehouse/retail.duckdb"


def test_missing_database_gives_actionable_message(monkeypatch, tmp_path):
    monkeypatch.setenv("RETAIL_DB_PATH", str(tmp_path / "missing.duckdb"))
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    assert not at.exception
    assert any("尚未找到数仓数据库" in item.value for item in at.info)
    assert not at.metric


@pytest.mark.skipif(not DATABASE.exists(), reason="先运行真实数据流水线")
def test_filters_match_fact_table_sql(monkeypatch):
    monkeypatch.setenv("RETAIL_DB_PATH", str(DATABASE))
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    assert not at.exception
    assert len(at.metric) == 9
    assert len(at.tabs) == 4
    at.date_input(key="date_range").set_value((date(2011, 1, 1), date(2011, 1, 31)))
    at.multiselect(key="country_filter").set_value(["France"])
    at.selectbox(key="trend_grain").set_value("日")
    at.run()
    assert not at.exception
    with duckdb.connect(str(DATABASE), read_only=True) as con:
        amount, orders, units, customers = con.execute("""
          SELECT SUM(f.line_amount), COUNT(DISTINCT f.invoice_no), SUM(f.quantity),
                 COUNT(DISTINCT CASE WHEN f.customer_key<>0 THEN f.customer_key END)
          FROM dwd.fact_transaction f JOIN dim.country c USING(country_key)
          WHERE f.is_positive_sale AND c.country='France'
            AND CAST(f.invoice_ts AS DATE) BETWEEN '2011-01-01' AND '2011-01-31'
        """).fetchone()
    expected = [f"£{float(amount):,.2f}", f"{orders:,}", f"{units:,}", f"{customers:,}",
                f"£{float(amount / Decimal(orders)):,.2f}"]
    assert [item.value for item in at.metric][:5] == expected


@pytest.mark.skipif(not DATABASE.exists(), reason="先运行真实数据流水线")
def test_empty_slice_and_incomplete_date_are_clear(monkeypatch):
    monkeypatch.setenv("RETAIL_DB_PATH", str(DATABASE))
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    at.date_input(key="date_range").set_value((date(2011, 1, 1), date(2011, 1, 1)))
    at.multiselect(key="country_filter").set_value(["France"])
    at.run()
    assert not at.exception
    assert any("没有有效正向销售记录" in item.value for item in at.info)
    assert [item.value for item in at.metric][1] == "0"
    at.date_input(key="date_range").set_value((date(2011, 1, 2),))
    at.run()
    assert not at.exception
    assert any("请选择" in item.value or "请再选择" in item.value for item in at.info)
