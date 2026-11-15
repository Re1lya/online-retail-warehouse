# 模块分工与接口

项目的四个模块通过分层数据表和统一查询接口连接，文件路径均相对于项目根目录。默认数据库为 `data/warehouse/retail.duckdb`。

## 数据获取与清洗：温家正

- `src/download_data.py`：下载原始 Excel，保存来源信息与文件校验值。
- `src/ingest.py`：`load_ods(con, source_path)` 将源数据写入 `ods.retail_raw`，增加来源行号、文件名和 SHA256。
- `sql/10_clean.sql`：生成 `stg.clean_transactions`，规范类型并标记取消、正向交易和完全重复记录。
- `src/quality.py`：`quality_report(con)` 统计缺失值、异常记录和有效交易数量。

ODS 和 STG 保留全部源记录，后续模型通过 `source_row_number` 回查数据。

## 数仓建模与明细层：梁宁炜

`sql/20_model.sql` 创建日期、商品、客户、国家四张维度表，以及交易事实表 `dwd.fact_transaction`。

事实表以来源行号为主键，保存订单号、时间、四个维度键、数量、单价、行金额和质量标记。每张维度表包含键值为 0 的未知成员。正向交易条件沿用 STG 的 `is_positive_sale` 字段。

## 指标与汇总层：虞上昕

`sql/30_marts.sql` 创建国家日、商品国家日和客户国家日汇总，并提供 ADS 查询视图。`pipeline.py` 按依赖顺序执行各模块，输出质量报告、分析结果和校验记录。

页面通过 `src/analytics.py` 查询数据：

| 接口 | 返回内容 |
|---|---|
| `bounds(con)` | 数据起止日期 |
| `countries(con)` | 可选国家列表 |
| `overview(con, start, end, countries=None)` | 五项核心指标 |
| `trend(con, start, end, countries=None, grain='month')` | 年、月或日趋势 |
| `products(con, start, end, countries=None, limit=10)` | 商品与业务项目排行 |
| `country_ranking(con, start, end, countries=None)` | 国家排行 |
| `customers(con, start, end, countries=None, limit=10)` | 已知客户排行 |

日期范围包含起止日期，国家列表为空表示全部国家。订单数和客户数在当前范围内重新去重。

## 可视化与系统集成：林游鑫

`app.py` 使用只读连接访问数据库，调用 `src.analytics` 获取指标和图表数据。页面包括销售概览、商品与业务项目、国家与客户三个页签，支持筛选、时间粒度切换和 CSV 下载。

页面缓存以数据库文件修改时间为版本。ETL 完成后，新的数据库版本对应新的查询结果。
