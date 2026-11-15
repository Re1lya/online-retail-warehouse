WITH totals AS (
 SELECT sales_amount,cancellation_amount,net_recorded_amount,order_count,customer_count FROM {{ ref('ads_overview') }}
), results AS (
 SELECT 'cube' AS source,sales_amount,cancellation_amount,net_recorded_amount,order_count,customer_count FROM {{ ref('ads_transaction_cube') }} WHERE grouping_id=7
 UNION ALL SELECT 'rollup',sales_amount,cancellation_amount,net_recorded_amount,order_count,customer_count FROM {{ ref('ads_time_rollup') }} WHERE grouping_id=7
) SELECT r.* FROM results r CROSS JOIN totals t WHERE r.sales_amount<>t.sales_amount OR r.cancellation_amount<>t.cancellation_amount
 OR r.net_recorded_amount<>t.net_recorded_amount OR r.order_count<>t.order_count OR r.customer_count<>t.customer_count
 UNION ALL SELECT 'net',sales_amount,cancellation_amount,net_recorded_amount,order_count,customer_count FROM totals WHERE net_recorded_amount<>sales_amount-cancellation_amount
