{{ config(schema='ads', alias='sales_daily') }}

SELECT * FROM {{ ref('dws_sales_day_country') }}
