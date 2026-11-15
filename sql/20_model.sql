-- 成员 B：维度建模。输入 stg.clean_transactions，保留每一条原始来源行。
-- 由 pipeline 在事务中按顺序执行；全量重建只替换本项目指定的 DIM/DWD 表。
CREATE SCHEMA IF NOT EXISTS dim;
CREATE SCHEMA IF NOT EXISTS dwd;

CREATE OR REPLACE TABLE dim.date (
    date_key INTEGER PRIMARY KEY,
    full_date DATE UNIQUE,
    year INTEGER,
    quarter INTEGER,
    month INTEGER,
    day INTEGER
);
INSERT INTO dim.date VALUES (0, NULL, NULL, NULL, NULL, NULL);
INSERT INTO dim.date
SELECT CAST(strftime(calendar_date, '%Y%m%d') AS INTEGER),
       CAST(calendar_date AS DATE),
       CAST(year(calendar_date) AS INTEGER),
       CAST(quarter(calendar_date) AS INTEGER),
       CAST(month(calendar_date) AS INTEGER),
       CAST(day(calendar_date) AS INTEGER)
FROM generate_series(
    (SELECT min(CAST(invoice_ts AS DATE)) FROM stg.clean_transactions),
    (SELECT max(CAST(invoice_ts AS DATE)) FROM stg.clean_transactions),
    INTERVAL 1 DAY
) AS calendar(calendar_date);

CREATE OR REPLACE TABLE dim.product (
    product_key BIGINT PRIMARY KEY,
    stock_code VARCHAR UNIQUE,
    description VARCHAR NOT NULL
);
INSERT INTO dim.product VALUES (0, NULL, '未知商品');
INSERT INTO dim.product
WITH candidates AS (
    SELECT trim(stock_code) AS stock_code,
           nullif(trim(description), '') AS description,
           row_number() OVER (
               PARTITION BY trim(stock_code)
               ORDER BY (nullif(trim(description), '') IS NOT NULL) DESC,
                        invoice_ts DESC NULLS LAST,
                        source_row_number DESC
           ) AS description_rank
    FROM stg.clean_transactions
    WHERE nullif(trim(stock_code), '') IS NOT NULL
)
SELECT row_number() OVER (ORDER BY stock_code) AS product_key,
       stock_code,
       coalesce(description, '商品名称缺失') AS description
FROM candidates
WHERE description_rank = 1;

CREATE OR REPLACE TABLE dim.customer (
    customer_key BIGINT PRIMARY KEY,
    customer_id VARCHAR UNIQUE
);
INSERT INTO dim.customer VALUES (0, NULL);
INSERT INTO dim.customer
SELECT row_number() OVER (ORDER BY customer_id), customer_id
FROM (
    SELECT DISTINCT trim(customer_id) AS customer_id
    FROM stg.clean_transactions
    WHERE nullif(trim(customer_id), '') IS NOT NULL
);

CREATE OR REPLACE TABLE dim.country (
    country_key BIGINT PRIMARY KEY,
    country VARCHAR UNIQUE NOT NULL
);
INSERT INTO dim.country VALUES (0, '未知国家');
INSERT INTO dim.country
SELECT row_number() OVER (ORDER BY country), country
FROM (
    SELECT DISTINCT trim(country) AS country
    FROM stg.clean_transactions
    WHERE nullif(trim(country), '') IS NOT NULL
      AND trim(country) <> '未知国家'
);

CREATE OR REPLACE TABLE dwd.fact_transaction (
    source_row_number BIGINT PRIMARY KEY,
    invoice_no VARCHAR,
    invoice_ts TIMESTAMP,
    date_key INTEGER NOT NULL CHECK (date_key >= 0),
    product_key BIGINT NOT NULL CHECK (product_key >= 0),
    customer_key BIGINT NOT NULL CHECK (customer_key >= 0),
    country_key BIGINT NOT NULL CHECK (country_key >= 0),
    quantity BIGINT,
    unit_price DECIMAL(18,4),
    line_amount DECIMAL(20,4),
    is_cancelled BOOLEAN NOT NULL,
    is_positive_sale BOOLEAN NOT NULL,
    is_exact_duplicate BOOLEAN NOT NULL
);
INSERT INTO dwd.fact_transaction
SELECT t.source_row_number,
       t.invoice_no,
       t.invoice_ts,
       coalesce(d.date_key, 0),
       coalesce(p.product_key, 0),
       coalesce(c.customer_key, 0),
       coalesce(g.country_key, 0),
       t.quantity,
       t.unit_price,
       CAST(CAST(t.quantity AS DECIMAL(18,0)) * t.unit_price AS DECIMAL(20,4)),
       coalesce(t.is_cancelled, false),
       coalesce(t.is_positive_sale, false),
       coalesce(t.is_exact_duplicate, false)
FROM stg.clean_transactions AS t
LEFT JOIN dim.date AS d ON CAST(t.invoice_ts AS DATE) = d.full_date
LEFT JOIN dim.product AS p ON nullif(trim(t.stock_code), '') = p.stock_code
LEFT JOIN dim.customer AS c ON nullif(trim(t.customer_id), '') = c.customer_id
LEFT JOIN dim.country AS g
    ON coalesce(nullif(trim(t.country), ''), '未知国家') = g.country;

COMMENT ON TABLE dim.date IS '连续日历维度；date_key=0表示未知日期，其他键为YYYYMMDD';
COMMENT ON TABLE dim.product IS '商品维度；采用源数据中最新非空描述，SCD1全量覆盖';
COMMENT ON TABLE dim.customer IS '客户编号维度；未知客户为0，不将国家固定绑定到客户';
COMMENT ON TABLE dim.country IS '交易记录国家维度；未知国家为0';
COMMENT ON TABLE dwd.fact_transaction IS '来源行级交易事实；包含销售、取消和异常记录，正向销售指标按is_positive_sale筛选';
