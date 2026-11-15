{{ config(schema='ads', alias='net_daily') }}

SELECT * FROM {{ ref('dws_net_day_country') }}
