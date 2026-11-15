{{ config(schema='dim', alias='date') }}

WITH calendar AS (
 SELECT calendar_date::DATE AS full_date FROM generate_series(
 (SELECT min(invoice_ts::DATE) FROM {{ ref('stg_clean_transactions') }}),
 (SELECT max(invoice_ts::DATE) FROM {{ ref('stg_clean_transactions') }}),INTERVAL 1 DAY) t(calendar_date)
), dates AS (SELECT NULL::DATE AS full_date UNION ALL SELECT full_date FROM calendar)
SELECT coalesce(strftime(full_date,'%Y%m%d')::INTEGER,0) AS date_key,full_date,
 year(full_date)::INTEGER AS year, quarter(full_date)::INTEGER AS quarter,
 month(full_date)::INTEGER AS month, day(full_date)::INTEGER AS day,
 isodow(full_date)::INTEGER AS iso_weekday, week(full_date)::INTEGER AS iso_week,
 strftime(full_date,'%G')::INTEGER AS iso_year,
 dayname(full_date) AS weekday_name, isodow(full_date) IN (6,7) AS is_weekend,
 date_trunc('month',full_date)::DATE AS month_start,last_day(full_date) AS month_end,
 strftime(full_date,'%Y-%m') AS year_month
FROM dates
