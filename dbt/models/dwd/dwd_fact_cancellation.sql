{{ config(schema='dwd', alias='fact_cancellation') }}

SELECT *,coalesce(invoice_no IS NOT NULL AND date_key<>0 AND product_key<>0
 AND quantity<0 AND unit_price>0,false) AS is_valid_cancellation
FROM {{ ref('dwd_fact_transaction') }} WHERE is_cancelled
