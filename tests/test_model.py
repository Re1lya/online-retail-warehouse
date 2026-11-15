"""模型边界验证。此处人工夹具仅用于单元测试，不是实际分析数据。"""

from decimal import Decimal
from pathlib import Path

import duckdb
import pytest


MODEL_SQL = (Path(__file__).resolve().parents[1] / "sql" / "20_model.sql").read_text(
    encoding="utf-8"
)


@pytest.fixture
def con():
    connection = duckdb.connect(":memory:")
    connection.execute(
        """
        CREATE SCHEMA stg;
        CREATE TABLE stg.clean_transactions (
            source_row_number BIGINT, invoice_no VARCHAR, stock_code VARCHAR,
            description VARCHAR, quantity BIGINT, invoice_ts TIMESTAMP,
            unit_price DECIMAL(18,4), customer_id VARCHAR, country VARCHAR,
            is_cancelled BOOLEAN, is_positive_sale BOOLEAN,
            is_exact_duplicate BOOLEAN
        );
        """
    )
    yield connection
    connection.close()


def load_boundary_fixture(con):
    con.execute(
        """
        INSERT INTO stg.clean_transactions VALUES
        (2, '100', 'P1', '旧名称', 2, '2011-01-01 09:00:00', 1.2345,
         '10001', 'United Kingdom', false, true, false),
        (3, '101', 'P1', '新名称', 3, '2011-01-02 09:00:00', 1.2345,
         '10001', 'France', false, true, false),
        (4, '102', 'P1', '', 1, '2011-01-03 09:00:00', 1.2345,
         NULL, 'United Kingdom', false, true, false),
        (5, 'C103', 'P2', '退货商品', -1, '2011-01-02 12:00:00', 2.0000,
         '10002', 'France', true, false, false),
        (6, NULL, NULL, NULL, NULL, NULL, NULL,
         NULL, NULL, false, false, false),
        (7, '100', 'P1', '旧名称', 2, '2011-01-01 09:00:00', 1.2345,
         '10001', 'United Kingdom', false, true, true);
        """
    )


def test_grain_unknown_members_and_no_join_amplification(con):
    load_boundary_fixture(con)
    con.execute(MODEL_SQL)
    assert con.execute("SELECT count(*) FROM dwd.fact_transaction").fetchone()[0] == 6
    assert con.execute(
        "SELECT count(DISTINCT source_row_number) FROM dwd.fact_transaction"
    ).fetchone()[0] == 6
    assert con.execute(
        "SELECT date_key, product_key, customer_key, country_key "
        "FROM dwd.fact_transaction WHERE source_row_number = 6"
    ).fetchone() == (0, 0, 0, 0)
    for dimension, key in [
        ("date", "date_key"),
        ("product", "product_key"),
        ("customer", "customer_key"),
        ("country", "country_key"),
    ]:
        assert con.execute(
            f"SELECT count(*) FROM dwd.fact_transaction f "
            f"LEFT JOIN dim.{dimension} d USING ({key}) WHERE d.{key} IS NULL"
        ).fetchone()[0] == 0
    assert con.execute("SELECT count(*) FROM dim.date").fetchone()[0] == 4


def test_latest_nonempty_description_and_transaction_country(con):
    load_boundary_fixture(con)
    con.execute(MODEL_SQL)
    assert con.execute(
        "SELECT description FROM dim.product WHERE stock_code = 'P1'"
    ).fetchone()[0] == "新名称"
    assert con.execute(
        "SELECT count(*) FROM dim.customer WHERE customer_id='10001'"
    ).fetchone()[0] == 1
    assert con.execute(
        "SELECT count(DISTINCT country_key) FROM dwd.fact_transaction f "
        "JOIN dim.customer c USING (customer_key) WHERE c.customer_id='10001'"
    ).fetchone()[0] == 2


def test_money_cancelled_and_duplicate_records_are_preserved(con):
    load_boundary_fixture(con)
    con.execute(MODEL_SQL)
    assert con.execute(
        "SELECT line_amount FROM dwd.fact_transaction WHERE source_row_number=2"
    ).fetchone()[0] == Decimal("2.4690")
    assert con.execute(
        "SELECT line_amount, is_cancelled, is_positive_sale "
        "FROM dwd.fact_transaction WHERE source_row_number=5"
    ).fetchone() == (Decimal("-2.0000"), True, False)
    assert con.execute(
        "SELECT is_exact_duplicate FROM dwd.fact_transaction WHERE source_row_number=7"
    ).fetchone()[0] is True
    assert con.execute(
        "SELECT count(*) FROM dwd.fact_transaction WHERE invoice_no='100'"
    ).fetchone()[0] == 2


def test_rebuild_is_deterministic(con):
    load_boundary_fixture(con)
    con.execute(MODEL_SQL)
    before = con.execute(
        "SELECT * FROM dwd.fact_transaction ORDER BY source_row_number"
    ).fetchall()
    con.execute(MODEL_SQL)
    after = con.execute(
        "SELECT * FROM dwd.fact_transaction ORDER BY source_row_number"
    ).fetchall()
    assert before == after


def test_empty_source_keeps_unknown_members(con):
    con.execute(MODEL_SQL)
    assert con.execute("SELECT count(*) FROM dwd.fact_transaction").fetchone()[0] == 0
    for dimension in ["date", "product", "customer", "country"]:
        assert con.execute(f"SELECT count(*) FROM dim.{dimension}").fetchone()[0] == 1
