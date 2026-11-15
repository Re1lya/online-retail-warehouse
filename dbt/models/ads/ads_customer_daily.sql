{{ config(schema='ads', alias='customer_daily') }}

SELECT * FROM {{ ref('dws_customer_day_country') }}
