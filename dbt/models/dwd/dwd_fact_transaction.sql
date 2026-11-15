{{ config(schema='dwd', alias='fact_transaction') }}

SELECT t.source_row_number,
       t.invoice_no,
       t.invoice_ts,
       coalesce(d.date_key, 0) AS date_key,
       coalesce(p.product_key, 0) AS product_key,
       coalesce(c.customer_key, 0) AS customer_key,
       coalesce(g.country_key, 0) AS country_key,
       t.quantity,
       t.unit_price,
       CAST(CAST(t.quantity AS DECIMAL(18,0)) * t.unit_price AS DECIMAL(20,4)) AS line_amount,
       coalesce(t.is_cancelled, false) AS is_cancelled,
       coalesce(t.is_positive_sale, false) AS is_positive_sale,
       coalesce(t.is_exact_duplicate, false) AS is_exact_duplicate
FROM {{ ref('stg_clean_transactions') }} AS t
LEFT JOIN {{ ref('dim_date') }} AS d ON CAST(t.invoice_ts AS DATE) = d.full_date
LEFT JOIN {{ ref('dim_product') }} AS p ON nullif(trim(t.stock_code), '') = p.stock_code
LEFT JOIN {{ ref('dim_customer') }} AS c ON nullif(trim(t.customer_id), '') = c.customer_id
LEFT JOIN {{ ref('dim_country') }} AS g
    ON coalesce(nullif(trim(t.country), ''), '未知国家') = g.country
