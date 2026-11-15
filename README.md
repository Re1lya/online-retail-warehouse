# 在线零售销售分析数仓系统的设计与实现

本项目用真实UCI Online Retail数据完成需求分析、四维星型建模、ODS/DWD/DWS/ADS分层、离线ETL、5项指标和3个中文可视化页面。项目采用四人分工，成员与模块对应关系见下方“团队交接”。

## 先看成果

- `期末大作业报告.docx`：按老师模板整理的完整报告。
- `docs/C_REQUIREMENTS.md`：业务需求、指标口径、验收标准。
- `docs/A_DATA.md`：数据来源、清洗和质量实测。
- `docs/B_MODEL.md`、`docs/model.svg`：概念/逻辑/物理设计、数据字典与模型图。
- `docs/D_DEMO.md`：运行与三分钟演示脚本。
- `data/exports/analysis.json`及CSV：真实分析结果。
- `data/exports/validation.json`、`test-results.xml`：运行时校验和自动化测试结果。
- `data/exports/business_caveats.json`：大额交易与取消记录的可追溯案例。

## 本地运行

建议使用Python 3.12（3.11及以上可尝试）。首次安装需要联网；数据文件和已生成数据库已包含，安装后看板可离线运行。无需安装数据库服务器。

在项目目录打开终端，执行：

```bash
python -m venv .venv
```

Windows PowerShell激活：`.venv\Scripts\Activate.ps1`；Windows命令提示符：`.venv\Scripts\activate.bat`；macOS/Linux：`source .venv/bin/activate`。

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

打开终端显示的本地地址，通常是 `http://localhost:8501`。看板提供日期、国家筛选及年/月/日切换。关闭终端或按Ctrl+C可停止。

## 从原始数据完整重建

先关闭看板，再运行：

```bash
python pipeline.py
python -m pytest -q
python -m streamlit run app.py
```

重建流程：Excel → ODS → STG类型规范 → DIM/DWD → DWS/ADS → 13项运行时校验 → 导出准备 → 数据库替换与结果发布。构建、校验、导出准备失败时保留旧库；多个导出文件与数据库之间不是跨文件事务，发布阶段意外中断后请关闭看板并重新运行流水线。

如果原始文件被移走，可从官方重新下载：

```bash
python -m src.download_data
```

重绘报告中的分析图（可选）：

```bash
python -m src.export_figures
```

## 指标口径

数据覆盖2010-12-01至2011-12-09，金额单位英镑GBP。有效正向交易要求单据/商品非空、日期有效、数量和单价>0、单据不以C开头。

| 指标 | 全量实测 |
|---|---:|
| 原始交易明细 | 541,909行 |
| 有效正向交易明细 | 530,104行 |
| 正向交易金额 | £10,666,684.54 |
| 销售订单数，正向单据去重 | 19,960 |
| 记录数量合计 | 5,588,376 |
| 已知购买客户数 | 4,338 |
| 平均订单金额 | £534.40 |

金额包含邮资、手工记账和调整项目，未抵扣取消记录，因此不代表纯商品净收入；记录数量合计也不等于纯实物销量。客户缺失的有效交易计入金额和订单，但不计入客户数。重复行仅标记保留。原始文件无业务明细唯一键，不能认定完全重复必然是导出错误。

2011年12月仅覆盖1日至9日，不能和完整月份直接比较月总量。商品23843有一笔£168,469.60正向记录及12分钟后相同客户/商品/单价、数量相反的取消记录，说明正向排行不可直接解释为已履约畅销榜。

## 代码导航

```text
app.py                  中文看板
pipeline.py             完整重建入口
src/download_data.py    官方数据下载与来源追踪
src/ingest.py           ODS导入
src/quality.py          数据质量统计
src/analytics.py        统一查询接口
src/validation.py       数据正确性校验
sql/10_clean.sql        清洗与质量标记
sql/20_model.sql        DIM和DWD
sql/30_marts.sql        DWS和ADS
tests/                  模型、指标与页面测试
data/raw/               官方原始Excel及来源凭据
data/warehouse/         已生成DuckDB数据库
data/exports/           分析、质量、校验及表清单
docs/                   四人模块文档与演示指南
assets/                 模型图、分析图和界面截图
```

## 团队交接

| 角色 | 已完成工作 | 主要解释内容 |
|---|---|---|
| A 温家正 | 下载、ODS、清洗、质量检查 | 来源可信、异常保留、真实数据限制 |
| B 梁宁炜 | 概念、逻辑、物理、DIM/DWD | 粒度、星型模型、未知成员、全量重建 |
| C 虞上昕 | 需求、指标、DWS/ADS、验证 | 可加/不可加指标、参数筛选、业务结论 |
| D 林游鑫 | 看板、导出、演示步骤 | 页面使用、多维操作、结果解释 |

## 数据来源与许可

Chen, D. (2015). Online Retail [Dataset]. UCI Machine Learning Repository. DOI: https://doi.org/10.24432/C5BW33 。官方页面：https://archive.ics.uci.edu/dataset/352/online%2Bretail 。数据许可CC BY 4.0，保留署名。数据原文件SHA256和下载时间见 `data/raw/SOURCE.json`。

本项目为单机离线课程实现，采用快照全量覆盖，未实现实时采集、SCD2、多写入者并发或生产级调度。仓库内报告保留原交付版本，提交前请补齐报告中的成员信息，并录制实际关键操作视频。期中检查PPT由温家正一人讲解，项目开发仍按四人分工。演示脚本不能代替录屏。
