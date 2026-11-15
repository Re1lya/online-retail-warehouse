-- 正向销售口径。保留去重标识到明细层，禁止跨期相加订单/客户去重数。
CREATE SCHEMA IF NOT EXISTS dws;
CREATE SCHEMA IF NOT EXISTS ads;

CREATE OR REPLACE VIEW ads.sales_detail AS
SELECT f.*, d.full_date AS sales_date, p.stock_code, p.description,
       c.customer_id, g.country
FROM dwd.fact_transaction f
JOIN dim.date d USING(date_key)
JOIN dim.product p USING(product_key)
JOIN dim.customer c USING(customer_key)
JOIN dim.country g USING(country_key)
WHERE f.is_positive_sale;

CREATE OR REPLACE TABLE dws.sales_day_country AS
SELECT sales_date, country, SUM(line_amount) AS sales_amount,
       SUM(quantity)::BIGINT AS units, COUNT(*) AS line_count,
       COUNT(DISTINCT invoice_no) AS daily_orders,
       COUNT(DISTINCT CASE WHEN customer_key <> 0 THEN customer_id END) AS daily_customers
FROM ads.sales_detail GROUP BY sales_date, country;

CREATE OR REPLACE TABLE dws.product_day_country AS
SELECT sales_date, country, product_key, stock_code, description,
       SUM(line_amount) AS sales_amount, SUM(quantity)::BIGINT AS units
FROM ads.sales_detail GROUP BY ALL;

CREATE OR REPLACE TABLE dws.customer_day_country AS
SELECT sales_date, country, customer_key, customer_id,
       SUM(line_amount) AS sales_amount, SUM(quantity)::BIGINT AS units
FROM ads.sales_detail WHERE customer_key <> 0 GROUP BY ALL;

-- ADS通过视图提供稳定接口；DWS负责持久化聚合，避免复制相同数据。
CREATE OR REPLACE VIEW ads.sales_daily AS SELECT * FROM dws.sales_day_country;
CREATE OR REPLACE VIEW ads.product_daily AS SELECT * FROM dws.product_day_country;
CREATE OR REPLACE VIEW ads.customer_daily AS SELECT * FROM dws.customer_day_country;
