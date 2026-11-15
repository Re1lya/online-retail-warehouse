{{ config(schema='dim', alias='customer') }}

WITH stats AS (
 SELECT customer_id,min(invoice_ts::DATE) AS first_transaction_date,
 max(invoice_ts::DATE) AS last_transaction_date,
 min(invoice_ts::DATE) FILTER(WHERE is_positive_sale) AS first_purchase_date,
 max(invoice_ts::DATE) FILTER(WHERE is_positive_sale) AS last_purchase_date,
 count(DISTINCT country) AS observed_country_count
 FROM {{ ref('stg_clean_transactions') }} WHERE customer_id IS NOT NULL GROUP BY customer_id
)
SELECT row_number() OVER(ORDER BY customer_id) AS customer_key,*,false AS is_unknown FROM stats
UNION ALL SELECT 0,NULL,NULL,NULL,NULL,NULL,0,true
