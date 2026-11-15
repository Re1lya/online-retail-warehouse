{{ config(schema='dws', alias='customer_day_country') }}

SELECT sales_date, country, customer_key, customer_id,
       SUM(line_amount) AS sales_amount, SUM(quantity)::BIGINT AS units
FROM {{ ref('dws_sales_detail') }} WHERE customer_key <> 0 GROUP BY ALL
