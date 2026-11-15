{{ config(schema='dwd', alias='fact_sales') }}

SELECT * FROM {{ ref('dwd_fact_transaction') }} WHERE is_positive_sale
