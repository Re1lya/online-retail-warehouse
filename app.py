"""在线零售销售分析看板；所有业务计算统一调用 src.analytics。"""
from __future__ import annotations

import json
import os
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("RETAIL_DB_PATH", ROOT / "data/warehouse/retail.duckdb"))

st.set_page_config(page_title="在线零售 · 销售分析", page_icon="◈", layout="wide")
st.markdown(
    """
    <style>
      .stApp { background:#f5f7fb; }
      .block-container { padding-top:4rem; padding-bottom:2rem; max-width:1500px; }
      [data-testid="stSidebar"] { background:#eaf0f7; }
      h1,h2,h3 { color:#142b48; }
      [data-testid="stMetric"] { background:white; border:1px solid #e1e8f0;
        border-radius:12px; padding:16px 18px; min-height:115px; }
      [data-testid="stMetricValue"] { font-size:clamp(1rem,1.4vw,1.45rem); color:#153553; }
      [data-testid="stMetricLabel"] { color:#52657a; }
      button[data-baseweb="tab"] { font-size:1rem; }
      .hero-kicker { color:#16847a; font-size:.8rem; letter-spacing:.16em; font-weight:700; }
      .hero-subtitle { color:#586b80; margin-top:-.4rem; margin-bottom:1.4rem; }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown('<div class="hero-kicker">RETAIL ANALYTICS / 离线数仓</div>', unsafe_allow_html=True)
st.title("在线零售销售分析")
st.markdown(
    '<div class="hero-subtitle">从销售趋势到商品、市场与客户，查看同一口径下的业务表现。</div>',
    unsafe_allow_html=True,
)

if not DB_PATH.is_file():
    st.info("尚未找到数仓数据库。请先在项目目录运行以下命令，完成数据导入与指标计算。")
    st.code("python pipeline.py", language="bash")
    st.caption("完成后刷新页面。首次运行前，请按 README 安装依赖并准备真实数据文件。")
    st.stop()

try:
    from src import analytics
except ImportError as exc:
    st.error("项目文件不完整，暂时无法加载指标模块。请解压完整项目后重试。")
    st.code(str(exc))
    st.stop()


@st.cache_data(show_spinner=False)
def dimensions(database: str, version: int):
    """文件修改时间作为缓存版本，重跑流水线后自动更新。"""
    with duckdb.connect(database, read_only=True) as con:
        return analytics.bounds(con), analytics.countries(con)


@st.cache_data(show_spinner=False)
def dashboard_data(database: str, version: int, start, end, selected: tuple, grain: str):
    with duckdb.connect(database, read_only=True) as con:
        filters = list(selected) or None
        return {
            "overview": analytics.overview(con, start, end, countries=filters),
            "trend": analytics.trend(con, start, end, countries=filters, grain=grain),
            "products": analytics.products(con, start, end, countries=filters, limit=10),
            "countries": analytics.country_ranking(con, start, end, countries=filters),
            "customers": analytics.customers(con, start, end, countries=filters, limit=10),
        }


def configure_chart(fig, *, height=360, money_axis="y"):
    fig.update_layout(
        template="plotly_white", height=height,
        font={"family": "Arial, PingFang SC, Microsoft YaHei, sans-serif", "color": "#243b53"},
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 8, "r": 12, "t": 12, "b": 10},
        hoverlabel={"bgcolor": "white"}, showlegend=False,
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="#e2e8f0", zeroline=False)
    if money_axis == "y":
        fig.update_yaxes(tickprefix="£", tickformat=",.0f")
    elif money_axis == "x":
        fig.update_xaxes(tickprefix="£", tickformat=",.0f", showgrid=True, gridcolor="#e2e8f0")
        fig.update_yaxes(showgrid=False)
    return fig


def export_table(df, label: str, filename: str):
    st.download_button(
        label, data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name=filename, mime="text/csv", key=filename,
    )


try:
    version = DB_PATH.stat().st_mtime_ns
    (min_date, max_date), country_options = dimensions(str(DB_PATH), version)
except Exception as exc:
    st.error("暂时无法读取数仓。请等待流水线结束，确认数据库构建成功后刷新页面。")
    with st.expander("查看错误详情"):
        st.code(str(exc))
    st.stop()

if min_date is None or max_date is None:
    st.warning("当前数仓没有可分析的有效销售记录，请检查流水线的数据质量报告。")
    st.stop()

with st.sidebar:
    st.header("分析范围")
    date_range = st.date_input(
        "交易日期", value=(min_date, max_date), min_value=min_date, max_value=max_date,
        format="YYYY/MM/DD", key="date_range",
    )
    selected_countries = st.multiselect(
        "客户所在国家", options=country_options, default=[],
        placeholder="全部国家", help="留空表示分析全部国家。", key="country_filter",
    )
    granularity = st.selectbox("趋势粒度", ["月", "日", "年"], key="trend_grain")
    st.divider()
    st.caption("数据范围")
    st.write(f"{min_date:%Y/%m/%d} — {max_date:%Y/%m/%d}")
    st.caption("来源：UCI Online Retail\n\n货币单位：英镑 GBP")
    st.markdown("[查看原始数据说明](https://archive.ics.uci.edu/dataset/352/online%2Bretail)")

if len(date_range) != 2:
    st.info("请再选择一个结束日期，以完成分析范围设置。")
    st.stop()
start, end = date_range
if start > end:
    st.warning("开始日期不能晚于结束日期。")
    st.stop()
grain = {"月": "month", "日": "day", "年": "year"}[granularity]

try:
    with st.spinner("正在读取销售分析结果…"):
        data = dashboard_data(str(DB_PATH), version, start, end, tuple(selected_countries), grain)
except Exception as exc:
    st.error("分析结果读取失败，请确认数仓各层已完成构建。")
    with st.expander("查看错误详情"):
        st.code(str(exc))
    st.stop()

scope_label = "全部国家" if not selected_countries else "、".join(selected_countries)
st.caption(f"当前范围：{start:%Y/%m/%d} — {end:%Y/%m/%d} · {scope_label}")
kpi = data["overview"]
cards = st.columns(5)
cards[0].metric("正向交易金额", f"£{float(kpi['sales_amount']):,.2f}")
cards[1].metric("销售订单数", f"{int(kpi['order_count']):,}")
cards[2].metric("记录数量合计", f"{int(kpi['units']):,}")
cards[3].metric("购买客户数", f"{int(kpi['customer_count']):,}")
cards[4].metric("平均订单金额", f"£{float(kpi['avg_order_value']):,.2f}")
st.caption("仅统计有效正向交易，包含邮资、手工记账及调整项目；取消交易未冲抵，金额非净收入。订单与客户按当前范围去重。")

if int(kpi["order_count"]) == 0:
    st.info("当前日期与国家组合没有有效正向销售记录，请调整筛选条件。")
    st.stop()

overview_tab, product_tab, market_tab = st.tabs(["销售概览", "商品与业务项目", "国家与客户"])

with overview_tab:
    st.subheader("交易金额趋势")
    trend = data["trend"].copy()
    if not trend.empty:
        fig = px.line(
            trend, x="period", y="sales_amount", markers=True,
            labels={"period": "交易时间", "sales_amount": "正向交易金额（GBP）"},
            color_discrete_sequence=["#138c83"],
        )
        fig.update_traces(line_width=3, fill="tozeroy", fillcolor="rgba(19,140,131,.07)",
                          hovertemplate="%{x}<br>交易金额 £%{y:,.2f}<extra></extra>")
        st.plotly_chart(configure_chart(fig, height=360), width="stretch")
    st.info("原始数据覆盖 2010/12/01 至 2011/12/09，2011年12月仅有部分日期。筛选后的首尾周期也可能不完整，比较趋势时请使用一致时间范围。", icon="ℹ️")
    with st.expander("查看趋势明细与下载"):
        display = trend.rename(columns={"period": "统计周期", "sales_amount": "正向交易金额（GBP）", "order_count": "销售订单数"})
        st.dataframe(display, hide_index=True, width="stretch")
        export_table(display, "下载趋势 CSV", "交易金额趋势.csv")
    with st.expander("指标口径与数据质量"):
        st.markdown("""
        - **正向交易金额**：有效正向交易的数量 × 单价之和，包含无法识别客户的有效交易。
        - **销售订单数**：当前筛选范围内的单据编号去重数。
        - **记录数量合计**：当前范围内有效正向交易的数量之和，包含非实物项目，不代表纯实物销量。
        - **购买客户数**：当前范围内已知客户编号的去重数。
        - **平均订单金额**：正向交易金额 ÷ 销售订单数。

        取消及其他非正向交易保留在明细层，不计入正向交易指标。完全相同的源记录标记为重复，
        因缺少业务明细行号，暂不自动删除。这里展示的是正向交易金额，不代表扣除取消后的净收入或利润。
        """)
        quality_path = ROOT / "data/exports/quality.json"
        if quality_path.is_file():
            # 质量报告由ETL生成，下载原始报告供复核；页面不另行计算质量指标。
            try:
                payload = json.loads(quality_path.read_text(encoding="utf-8"))
                st.download_button("下载数据质量报告", json.dumps(payload, ensure_ascii=False, indent=2),
                                   "数据质量报告.json", "application/json", key="quality_json")
            except (ValueError, OSError):
                st.caption("数据质量报告暂不可读取，可在项目导出目录查看。")

with product_tab:
    st.subheader("商品与业务项目金额 Top 10")
    st.caption("按原始商品编码统计，包含邮资、手工记账及调整项目。")
    products = data["products"].copy()
    if products.empty:
        st.info("当前范围没有可展示的商品。")
    else:
        products["商品标签"] = products["stock_code"].astype(str) + " · " + products["description"].fillna("未知商品").astype(str).str.slice(0, 32)
        fig = px.bar(
            products.sort_values("sales_amount"), x="sales_amount", y="商品标签", orientation="h",
            labels={"sales_amount": "正向交易金额（GBP）", "商品标签": ""},
            color_discrete_sequence=["#168c83"], custom_data=["description", "units"],
        )
        fig.update_traces(hovertemplate="%{customdata[0]}<br>交易金额 £%{x:,.2f}<br>记录数量 %{customdata[1]:,}<extra></extra>")
        st.plotly_chart(configure_chart(fig, height=430, money_axis="x"), width="stretch")
        table = products.drop(columns=["商品标签"]).rename(columns={"stock_code": "商品编号", "description": "商品或业务项目", "sales_amount": "正向交易金额（GBP）", "units": "记录数量合计"})
        st.dataframe(table, hide_index=True, width="stretch")
        export_table(table, "下载商品排行 CSV", "商品与业务项目排行.csv")
    st.caption("名称取维度表中的有效描述。记录数量合计包含非实物项目；取消记录未冲抵，排行不能直接解释为实物净销量。")

with market_tab:
    country_col, customer_col = st.columns([1, 1])
    with country_col:
        st.subheader("国家交易金额 Top 10")
        ranking = data["countries"].copy()
        if not ranking.empty:
            top_countries = ranking.sort_values("sales_amount", ascending=False).head(10).sort_values("sales_amount")
            fig = px.bar(top_countries, x="sales_amount", y="country", orientation="h",
                         labels={"sales_amount": "正向交易金额（GBP）", "country": ""},
                         color_discrete_sequence=["#234e70"])
            fig.update_traces(hovertemplate="%{y}<br>交易金额 £%{x:,.2f}<extra></extra>")
            st.plotly_chart(configure_chart(fig, height=380, money_axis="x"), width="stretch")
            country_table = ranking.rename(columns={"country": "客户所在国家", "sales_amount": "正向交易金额（GBP）", "order_count": "销售订单数"})
            export_table(country_table, "下载全部国家排行 CSV", "国家销售排行.csv")
        else:
            st.info("当前范围没有国家销售结果。")
    with customer_col:
        st.subheader("客户交易金额 Top 10")
        customer_table = data["customers"].rename(columns={"customer_id": "客户编号", "sales_amount": "正向交易金额（GBP）", "order_count": "销售订单数"})
        if customer_table.empty:
            st.info("当前范围没有可识别的购买客户。未知客户交易仍计入交易金额。")
        else:
            st.dataframe(customer_table, hide_index=True, width="stretch", height=380)
            export_table(customer_table, "下载客户排行 CSV", "客户消费排行.csv")
        st.caption("客户仅以原始编号展示。国家表示该交易记录中的客户所在国家。")

st.divider()
st.caption("在线零售销售分析数仓系统 · 真实历史交易 · ODS → DIM / DWD → DWS → ADS")
