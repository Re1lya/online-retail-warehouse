# 四人协作接口约定

项目：在线零售销售分析数仓系统的设计与实现。A 数据，B 模型，C 需求指标，D 展示集成。角色为模拟分工，未虚构真实姓名学号。

Python 3.11+；DuckDB；pandas/openpyxl；Streamlit/Plotly。路径统一相对项目根目录。默认数据库 data/warehouse/retail.duckdb。

## A 输出
- src/ingest.py：load_ods(con, source_path) -> dict。导入真实 Excel；创建 ods.retail_raw；原始8列使用 snake_case 英文字段；额外 source_row_number 从2开始、source_file、source_sha256。
- sql/10_clean.sql：创建 stg.clean_transactions 视图/表，保留全部原始行。字段：source_row_number BIGINT，invoice_no VARCHAR，stock_code VARCHAR，description VARCHAR，quantity BIGINT，invoice_ts TIMESTAMP，unit_price DECIMAL(18,4)，customer_id VARCHAR（缺失NULL），country VARCHAR（缺失'未知国家'），is_cancelled BOOLEAN（invoice_no以C开头，忽略大小写），is_positive_sale BOOLEAN（单据和商品非空、日期有效、quantity>0、unit_price>0且非取消），is_exact_duplicate BOOLEAN（原始8字段完全相同分组中第2条起为true）。不贸然删除重复行，质量报告说明局限。不可编造数据。
- src/download_data.py 命令行下载官方真实数据，data/raw/Online Retail.xlsx；docs/A_DATA.md + data/raw/SOURCE.json 源站、许可、下载URL、SHA256、获取时间。
- src/quality.py：quality_report(con)->dict，基于ods/stg给出行数、异常计数、有效销售计数等。

## B 输出
- sql/20_model.sql：创建 dim.date（date_key INTEGER, full_date DATE, year INTEGER, quarter INTEGER, month INTEGER, day INTEGER）、dim.product（product_key BIGINT, stock_code VARCHAR, description VARCHAR）、dim.customer（customer_key BIGINT, customer_id VARCHAR）、dim.country（country_key BIGINT,country VARCHAR）。每维均有0号未知成员；日期0号full_date NULL。
- dwd.fact_transaction：source_row_number BIGINT主键，invoice_no VARCHAR，invoice_ts TIMESTAMP，date_key INTEGER，product_key BIGINT，customer_key BIGINT，country_key BIGINT，quantity BIGINT，unit_price DECIMAL(18,4)，line_amount DECIMAL(20,4)，is_cancelled BOOLEAN，is_positive_sale BOOLEAN，is_exact_duplicate BOOLEAN。保留全部来源行；空/非法字段通过未知维度或NULL保留。
- docs/B_MODEL.md：概念、逻辑、物理、数据字典、粒度、维度更新策略、约束说明。SQL可重复重建。

## C 输出（集成负责人）
- sql/30_marts.sql：DWS日-国家、日-商品-国家、日-客户-国家汇总；ADS维度展开交易视图与指标查询。
- src/analytics.py 固定接口：bounds(con)->(date,date)；countries(con)->list[str]；overview(con,start,end,countries=None)->dict(sales_amount,order_count,units,customer_count,avg_order_value)；trend(con,start,end,countries=None,grain='month')->DataFrame(period,sales_amount,order_count)；products(...,limit=10)->DataFrame(stock_code,description,sales_amount,units)；country_ranking(...)->DataFrame(country,sales_amount,order_count)；customers(...,limit=10)->DataFrame(customer_id,sales_amount,order_count)。countries=[]等同全选。筛选日期两端包含。所有指标采用正向销售。金额GBP。order_count按InvoiceNo去重，客户去重排除未知，跨区间重新计算而不累加去重数。
- pipeline.py 完整离线流水线，输出质量报告、实测分析、验证结果；需求文档、测试、README、最终项目报告。

## D 输出
- app.py：中文Streamlit，3个页面/页签：销售概览、商品分析、国家与客户。日期/国家筛选；年/月/日趋势；指标卡；图表；结果CSV下载；空结果/库不存在有清晰提示；金额英镑；提示首尾月不完整及正向销售口径。只读打开DB，调用src.analytics。不重新计算口径。局部SQL若确需请告知C。
- assets/（如需要）；docs/D_DEMO.md 包括启动、3分钟演示脚本、答辩讲解及组内交接。

## 共同边界
只做本地可运行项目，不发布到互联网。各人仅编辑自己负责的文件。数据下载、安装依赖和流水线由负责人协调，避免数据库多进程写入。每人提供独立可复核成果，不宣称未执行的验证。
