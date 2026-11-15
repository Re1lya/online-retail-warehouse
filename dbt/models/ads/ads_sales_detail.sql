{{ config(schema='ads', alias='sales_detail') }}

SELECT * FROM {{ ref('dws_sales_detail') }}
