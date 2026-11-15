{{ config(schema='stg', alias='clean_transactions') }}

WITH normalized AS (
    SELECT source_row_number,
           NULLIF(TRIM(invoice_no), '') AS invoice_no,
           NULLIF(TRIM(stock_code), '') AS stock_code,
           NULLIF(TRIM(description), '') AS description,
           CASE WHEN TRY_CAST(quantity AS DECIMAL(20,4)) = TRUNC(TRY_CAST(quantity AS DECIMAL(20,4)))
                THEN TRY_CAST(quantity AS BIGINT) END AS quantity,
           TRY_CAST(invoice_date AS TIMESTAMP) AS invoice_ts,
           TRY_CAST(unit_price AS DECIMAL(18,4)) AS unit_price,
           NULLIF(TRIM(customer_id), '') AS customer_id,
           COALESCE(NULLIF(TRIM(country), ''), '未知国家') AS country,
           ROW_NUMBER() OVER (
               PARTITION BY invoice_no, stock_code, description, quantity,
                            invoice_date, unit_price, customer_id, country
               ORDER BY source_row_number
           ) > 1 AS is_exact_duplicate
    FROM {{ source('raw', 'retail_raw') }}
), classified AS (
    SELECT *, COALESCE(UPPER(invoice_no) LIKE 'C%', FALSE) AS is_cancelled
    FROM normalized
)
SELECT source_row_number, invoice_no, stock_code, description, quantity, invoice_ts,
       unit_price, customer_id, country, is_cancelled,
       COALESCE(invoice_no IS NOT NULL AND stock_code IS NOT NULL
                AND invoice_ts IS NOT NULL AND quantity > 0 AND unit_price > 0
                AND NOT is_cancelled, FALSE) AS is_positive_sale,
       is_exact_duplicate
FROM classified
ORDER BY source_row_number
