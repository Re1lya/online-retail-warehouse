{{ config(schema='dws', alias='sales_detail') }}

SELECT f.*,d.full_date AS sales_date,p.stock_code,p.description,c.customer_id,g.country
FROM {{ ref('dwd_fact_sales') }} f
JOIN {{ ref('dim_date') }} d USING(date_key) JOIN {{ ref('dim_product') }} p USING(product_key)
JOIN {{ ref('dim_customer') }} c USING(customer_key) JOIN {{ ref('dim_country') }} g USING(country_key)
