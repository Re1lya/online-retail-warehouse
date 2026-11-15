{{ config(schema='dim', alias='country') }}

WITH countries AS (
 SELECT DISTINCT country FROM {{ ref('stg_clean_transactions') }} WHERE country <> '未知国家'
), keyed AS (SELECT row_number() OVER(ORDER BY country) AS country_key,country FROM countries
 UNION ALL SELECT 0,'未知国家')
SELECT *,country='United Kingdom' AS is_home_market,
 CASE WHEN country='未知国家' THEN '未知' WHEN country='United Kingdom' THEN '本土' ELSE '海外' END AS market_type
FROM keyed
