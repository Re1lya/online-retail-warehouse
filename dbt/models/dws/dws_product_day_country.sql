{{ config(schema='dws', alias='product_day_country') }}

SELECT sales_date, country, product_key, stock_code, description,
       SUM(line_amount) AS sales_amount, SUM(quantity)::BIGINT AS units
FROM {{ ref('dws_sales_detail') }} GROUP BY ALL
