SELECT 1 AS failed WHERE (SELECT count(*) FROM {{ ref('dwd_fact_cancellation') }})<>(SELECT count(*) FROM {{ ref('stg_clean_transactions') }} WHERE is_cancelled)
