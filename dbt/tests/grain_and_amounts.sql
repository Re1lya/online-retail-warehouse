WITH amounts AS (
 SELECT (SELECT count(*) FROM {{ ref('dwd_fact_transaction') }}) AS facts,
 (SELECT count(*) FROM {{ source('raw','retail_raw') }}) AS raw,
 (SELECT coalesce(sum(quantity*unit_price),0) FROM {{ ref('stg_clean_transactions') }} WHERE is_positive_sale) AS expected_sales,
 (SELECT coalesce(sum(line_amount),0) FROM {{ ref('dwd_fact_sales') }}) AS actual_sales,
 (SELECT coalesce(sum(sales_amount),0) FROM {{ ref('dws_sales_day_country') }}) AS daily_sales,
 (SELECT coalesce(sum(sales_amount),0) FROM {{ ref('dws_product_day_country') }}) AS product_sales,
 (SELECT coalesce(sum(line_amount),0) FROM {{ ref('dwd_fact_sales') }} WHERE customer_key<>0) AS known_sales,
 (SELECT coalesce(sum(sales_amount),0) FROM {{ ref('dws_customer_day_country') }}) AS customer_sales
) SELECT * FROM amounts WHERE facts<>raw OR expected_sales<>actual_sales OR actual_sales<>daily_sales OR actual_sales<>product_sales OR known_sales<>customer_sales
