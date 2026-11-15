{{ config(schema='ads', alias='overview') }}

WITH totals AS (SELECT coalesce(sum(line_amount) FILTER(WHERE entry_type='sale'),0)::DECIMAL(20,4) AS sales_amount,
 -coalesce(sum(line_amount) FILTER(WHERE entry_type='cancellation'),0)::DECIMAL(20,4) AS cancellation_amount,
 coalesce(sum(line_amount),0)::DECIMAL(20,4) AS net_recorded_amount,
 count(DISTINCT invoice_no) FILTER(WHERE entry_type='sale') AS order_count,
 count(DISTINCT invoice_no) FILTER(WHERE entry_type='cancellation') AS cancellation_order_count,
 count(DISTINCT customer_id) FILTER(WHERE entry_type='sale') AS customer_count,
 coalesce(sum(quantity) FILTER(WHERE entry_type='sale'),0)::BIGINT AS units,
 -coalesce(sum(quantity) FILTER(WHERE entry_type='cancellation'),0)::BIGINT AS cancellation_units FROM {{ ref('dws_transaction_detail') }})
SELECT *,sales_amount/nullif(order_count,0) AS avg_order_value,
 cancellation_amount/nullif(sales_amount,0) AS cancellation_amount_ratio FROM totals
