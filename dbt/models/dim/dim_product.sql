{{ config(schema='dim', alias='product') }}

WITH known AS (WITH candidates AS (
    SELECT trim(stock_code) AS stock_code,
           nullif(trim(description), '') AS description,
           row_number() OVER (
               PARTITION BY trim(stock_code)
               ORDER BY (nullif(trim(description), '') IS NOT NULL) DESC,
                        invoice_ts DESC NULLS LAST,
                        source_row_number DESC
           ) AS description_rank
    FROM {{ ref('stg_clean_transactions') }}
    WHERE nullif(trim(stock_code), '') IS NOT NULL
)
SELECT row_number() OVER (ORDER BY stock_code) AS product_key,
       stock_code,
       coalesce(description, '商品名称缺失') AS description
FROM candidates
WHERE description_rank = 1) SELECT * FROM known UNION ALL SELECT 0,NULL,'未知商品'
