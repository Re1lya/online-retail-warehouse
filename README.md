# 在线零售销售分析数仓系统的设计与实现

这是我们《数据仓库》课程的大作业。我们选用 UCI Online Retail 数据集，使用 Python、dbt、DuckDB 和 Streamlit 搭建零售交易分析系统，完成数据清洗、维度建模、分层汇总和可视化。

系统可以按日期和国家筛选交易数据，查看销售与取消金额趋势、商品和客户排行，并通过多维交叉表比较不同市场。

## 技术方案

| 技术 | 用途 |
|---|---|
| Python、pandas、openpyxl | 读取 Excel、处理数据、运行 ETL |
| dbt-core、dbt-duckdb | 管理分层 SQL、模型依赖、数据测试与血缘文档 |
| DuckDB、SQL | 保存分层表，执行 CUBE / ROLLUP 多维汇总 |
| Streamlit、Plotly | 页面筛选、图表展示和 CSV 下载 |
| pytest | 检查模型、指标和页面功能 |

数仓采用 Kimball 维度建模，以原始交易明细为事实粒度。销售与取消两个业务过程共享日期、商品、客户和国家四个维度。数据分为 ODS、STG、DIM、DWD、DWS 和 ADS 层，分别负责原始数据保存、清洗、维度管理、明细存储、汇总和应用查询。

## 本地运行

推荐使用 Python 3.12。仓库中包含原始数据和已生成的数据库，安装依赖后即可启动页面。

```bash
git clone https://github.com/Re1lya/online-retail-warehouse.git
cd online-retail-warehouse
python -m venv .venv
```

激活虚拟环境：

- Windows PowerShell：`.venv\Scripts\Activate.ps1`
- Windows CMD：`.venv\Scripts\activate.bat`
- macOS / Linux：`source .venv/bin/activate`

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

在浏览器打开终端显示的地址，默认是 `http://localhost:8501`。

### 重新生成数据库

关闭页面服务后，在项目目录执行：

```bash
python pipeline.py
python -m pytest -q
python -m streamlit run app.py
```

`pipeline.py` 导入 ODS 后执行 `dbt build`，完成 23 个分层模型和 34 项数据测试，再核对指标并发布数据库。构建同时生成 `docs/dbt/index.html`，用浏览器打开可查看模型说明、字段和血缘图。

模型设计与总线矩阵见 [模型设计](docs/B_MODEL.md)，指标体系见 [需求分析](docs/C_REQUIREMENTS.md)。

原始文件缺失时，可以运行 `python -m src.download_data` 重新下载。报告中的分析图可通过 `python -m src.export_figures` 生成。

## 页面功能

| 页面 | 内容 |
|---|---|
| 销售概览 | 五项指标、年/月/日交易趋势 |
| 商品与业务项目 | 金额 Top 10、记录数量和明细表 |
| 国家与客户 | 国家交易金额排行、已知客户排行 |
| 取消与多维分析 | 取消与净额趋势、组合维度、交叉表、时间层级上卷 |

四个页面共用日期和国家筛选条件，结果可以下载为 CSV。

## 数据与指标

数据来自 [UCI Online Retail](https://archive.ics.uci.edu/dataset/352/online%2Bretail)，共 541,909 条记录，覆盖 2010-12-01 至 2011-12-09，金额单位为英镑。

我们将单据和商品编号有效、日期有效、数量和单价大于零、且单据不以 C 开头的记录计入正向交易。取消和异常记录保留在明细层，完全重复行保留并标记。客户编号缺失的交易仍计入金额和订单数，但不计入已知客户数。

| 指标 | 全量结果 |
|---|---:|
| 正向交易金额 | £10,666,684.54 |
| 销售订单数 | 19,960 |
| 记录数量合计 | 5,588,376 |
| 已知购买客户数 | 4,338 |
| 平均订单金额 | £534.40 |
| 取消记录金额 | £896,812.49 |
| 净交易记录金额 | £9,769,872.05 |
| 取消单据数 | 3,836 |
| 取消金额占比 | 8.41% |

正向交易金额包含邮费和人工调整项目；净交易记录金额另外扣除有效取消记录的金额。取消按发生日期统计，取消金额占比不是同批订单的退货率。订单和客户在当前筛选范围内分别去重，平均订单金额按总金额除以订单数计算。2011 年 12 月的数据截至 9 日。

## 项目结构

```text
app.py                  Streamlit 页面
pipeline.py             ETL 入口
src/                    数据导入、质量检查和指标查询
dbt/                    分层模型、数据测试、配置与依赖
tests/                  模型、指标和页面测试
data/raw/               原始 Excel 和来源信息
data/warehouse/         DuckDB 数据库
data/exports/           分析结果和校验记录
docs/                   需求、总线矩阵、模型说明与 dbt 血缘文档
assets/                 模型图、分析图和页面截图
期末大作业报告.docx       项目报告
```

## 小组分工

| 成员 | 负责内容 |
|---|---|
| 温家正 | 数据获取、ODS 导入、清洗和数据质量检查 |
| 梁宁炜 | 概念、逻辑和物理设计，DIM / DWD 开发 |
| 虞上昕 | 需求与指标定义，DWS / ADS 开发和数据校验 |
| 林游鑫 | 可视化页面、结果导出和系统集成 |

## 数据来源

Chen, D. (2015). *Online Retail*. UCI Machine Learning Repository. [DOI: 10.24432/C5BW33](https://doi.org/10.24432/C5BW33)。数据采用 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 许可，原始文件的下载信息和校验值保存在 `data/raw/SOURCE.json`。
