{{ config(schema='dws', alias='sales_day_country') }}

SELECT sales_date, country, SUM(line_amount) AS sales_amount,
       SUM(quantity)::BIGINT AS units, COUNT(*) AS line_count,
       COUNT(DISTINCT invoice_no) AS daily_orders,
       COUNT(DISTINCT CASE WHEN customer_key <> 0 THEN customer_id END) AS daily_customers
FROM {{ ref('dws_sales_detail') }} GROUP BY sales_date, country
