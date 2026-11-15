{{ config(schema='ads', alias='product_daily') }}

SELECT * FROM {{ ref('dws_product_day_country') }}
