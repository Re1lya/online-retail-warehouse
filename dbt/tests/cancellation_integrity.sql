SELECT source_row_number FROM {{ ref('dwd_fact_cancellation') }} WHERE NOT is_cancelled
UNION ALL SELECT source_row_number FROM {{ ref('dwd_fact_sales') }} WHERE is_cancelled OR line_amount<=0
UNION ALL SELECT c.source_row_number FROM {{ ref('dwd_fact_cancellation') }} c JOIN {{ ref('dwd_fact_sales') }} s USING(source_row_number)
UNION ALL SELECT source_row_number FROM {{ ref('dwd_fact_cancellation') }} WHERE is_valid_cancellation AND (line_amount>=0 OR line_amount IS NULL)
