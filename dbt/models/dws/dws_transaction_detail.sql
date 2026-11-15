{{ config(schema='dws', alias='transaction_detail') }}

WITH events AS (
 SELECT source_row_number,invoice_no,date_key,product_key,customer_key,country_key,quantity,line_amount,'sale' AS entry_type FROM {{ ref('dwd_fact_sales') }}
 UNION ALL
 SELECT source_row_number,invoice_no,date_key,product_key,customer_key,country_key,quantity,line_amount,'cancellation' AS entry_type FROM {{ ref('dwd_fact_cancellation') }} WHERE is_valid_cancellation
)
SELECT f.*,d.full_date AS sales_date,d.year,d.quarter,d.month,d.month_start,
 p.stock_code,p.description,c.customer_id,g.country,g.market_type
FROM events f JOIN {{ ref('dim_date') }} d USING(date_key) JOIN {{ ref('dim_product') }} p USING(product_key)
JOIN {{ ref('dim_customer') }} c USING(customer_key) JOIN {{ ref('dim_country') }} g USING(country_key)
