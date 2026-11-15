"""Measured data-quality checks. Counts can overlap and are not additive."""
from __future__ import annotations


def quality_report(con) -> dict:
    cursor = con.execute("""
        SELECT COUNT(*) AS source_rows,
               COUNT(*) FILTER (WHERE invoice_no IS NULL) AS missing_invoice_no,
               COUNT(*) FILTER (WHERE stock_code IS NULL) AS missing_stock_code,
               COUNT(*) FILTER (WHERE description IS NULL) AS missing_description,
               COUNT(*) FILTER (WHERE quantity IS NULL) AS invalid_quantity,
               COUNT(*) FILTER (WHERE quantity <= 0) AS nonpositive_quantity,
               COUNT(*) FILTER (WHERE invoice_ts IS NULL) AS invalid_invoice_date,
               COUNT(*) FILTER (WHERE unit_price IS NULL) AS invalid_unit_price,
               COUNT(*) FILTER (WHERE unit_price = 0) AS zero_unit_price,
               COUNT(*) FILTER (WHERE unit_price < 0) AS negative_unit_price,
               COUNT(*) FILTER (WHERE customer_id IS NULL) AS missing_customer_id,
               COUNT(*) FILTER (WHERE country = '未知国家') AS missing_country,
               COUNT(*) FILTER (WHERE is_cancelled) AS cancelled_rows,
               COUNT(*) FILTER (WHERE is_exact_duplicate) AS exact_duplicate_extra_rows,
               COUNT(*) FILTER (WHERE is_positive_sale) AS positive_sale_rows,
               COUNT(*) FILTER (WHERE NOT is_positive_sale) AS excluded_from_positive_sales_rows,
               COUNT(*) FILTER (WHERE is_positive_sale AND customer_id IS NULL) AS positive_sales_unknown_customer_rows,
               COUNT(*) FILTER (WHERE is_positive_sale AND is_exact_duplicate) AS positive_sales_duplicate_extra_rows,
               MIN(invoice_ts) AS min_invoice_ts, MAX(invoice_ts) AS max_invoice_ts,
               COUNT(DISTINCT stock_code) AS distinct_stock_codes,
               COUNT(DISTINCT customer_id) AS distinct_known_customers,
               COUNT(DISTINCT country) AS distinct_countries
        FROM stg.clean_transactions
    """)
    result = dict(zip([item[0] for item in cursor.description], cursor.fetchone()))
    for key in ("min_invoice_ts", "max_invoice_ts"):
        result[key] = result[key].isoformat(sep=" ") if result[key] is not None else None
    result["ods_rows"] = con.execute("SELECT COUNT(*) FROM ods.retail_raw").fetchone()[0]
    result["staging_preserves_all_source_rows"] = result["ods_rows"] == result["source_rows"]
    result["counts_overlap"] = True
    result["duplicate_policy"] = "保留并标记完全重复的后续行。源数据无业务行号，不能确认重复导出；正向销售指标保留这些行。"
    result["customer_policy"] = "未知客户销售计入销售额、订单数和件数；客户数与客户排行排除未知客户。"
    result["sales_policy"] = "单据和商品非空、时间有效、数量及单价大于零、单据非C开头；正向交易金额为GBP，含邮资、手工及调整项目，非净收入。"
    result["source_metadata_note"] = "UCI页面的缺失值字段标注与实际工作簿不一致；本项目使用实际逐字段扫描结果。"
    return result
