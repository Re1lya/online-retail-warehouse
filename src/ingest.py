"""Excel to ODS ingestion; source values and original Excel row IDs are retained."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

SOURCE_COLUMNS = {
    "InvoiceNo": "invoice_no",
    "StockCode": "stock_code",
    "Description": "description",
    "Quantity": "quantity",
    "InvoiceDate": "invoice_date",
    "UnitPrice": "unit_price",
    "CustomerID": "customer_id",
    "Country": "country",
}


def load_ods(con, source_path: str | Path) -> dict:
    """Rebuild ODS using untrimmed text values, plus row-level provenance.

    The untouched workbook is the exact binary source of truth. Strings avoid
    destroying alphanumeric invoice/product identifiers; cleaning happens in SQL.
    """
    source_path = Path(source_path).resolve()
    with source_path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    frame = pd.read_excel(source_path, sheet_name=0, dtype=str, engine="openpyxl")
    missing = set(SOURCE_COLUMNS) - set(frame.columns)
    extra = set(frame.columns) - set(SOURCE_COLUMNS)
    if missing or extra:
        raise ValueError(f"Excel字段与预期不同，缺失={sorted(missing)}，多余={sorted(extra)}")
    frame = frame[list(SOURCE_COLUMNS)].rename(columns=SOURCE_COLUMNS)
    frame.insert(0, "source_row_number", range(2, len(frame) + 2))
    frame["source_file"] = source_path.name
    frame["source_sha256"] = digest
    con.execute("CREATE SCHEMA IF NOT EXISTS ods")
    con.register("_excel_import", frame)
    try:
        con.execute("""
            CREATE OR REPLACE TABLE ods.retail_raw AS
            SELECT source_row_number::BIGINT AS source_row_number,
                   invoice_no::VARCHAR AS invoice_no, stock_code::VARCHAR AS stock_code,
                   description::VARCHAR AS description, quantity::VARCHAR AS quantity,
                   invoice_date::VARCHAR AS invoice_date, unit_price::VARCHAR AS unit_price,
                   customer_id::VARCHAR AS customer_id, country::VARCHAR AS country,
                   source_file::VARCHAR AS source_file, source_sha256::VARCHAR AS source_sha256
            FROM _excel_import
        """)
    finally:
        con.unregister("_excel_import")
    return {
        "source_file": source_path.name,
        "source_sha256": digest,
        "row_count": len(frame),
        "column_count": len(SOURCE_COLUMNS),
        "first_source_row": 2 if len(frame) else None,
        "last_source_row": len(frame) + 1 if len(frame) else None,
    }
