"""从真实分析结果生成报告插图。运行：python -m src.export_figures。

可选 --analysis/--output/--font 参数。仅使用本地字体和 matplotlib，不请求图片服务。
优先寻找中文字体；无可用中文字体时给出安装提示，避免静默输出方框字。
"""
from __future__ import annotations

import argparse
import calendar
import json
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager, ft2font
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from matplotlib.ticker import FuncFormatter


ROOT = Path(__file__).resolve().parents[1]
NAVY = "#183650"
TEAL = "#087f83"
BLUE = "#346c94"
INK = "#243c4e"
MUTED = "#5a6d7b"
GRID = "#dde5eb"
PALE = "#eaf3f5"
FOOTNOTE = "口径：包含邮资、手工记账和调整项目；取消记录未冲抵，非净收入。"


def select_font(explicit: Path | None = None) -> str:
    candidates = []
    if explicit is not None:
        if not explicit.is_file():
            raise FileNotFoundError(f"字体不存在：{explicit}")
        candidates.append(str(explicit))
    for family in [
        "Arial Unicode MS", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC",
        "Source Han Sans SC", "WenQuanYi Micro Hei", "Heiti SC", "SimHei",
    ]:
        try:
            candidates.append(font_manager.findfont(family, fallback_to_default=False))
        except ValueError:
            pass
    # 常见系统字体位置仅作为可选候选，不依赖某台机器的个人目录。
    for system_path in [
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/PingFang.ttc",
        "C:/Windows/Fonts/msyh.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]:
        if Path(system_path).is_file():
            candidates.append(system_path)
    for path in dict.fromkeys(candidates):
        try:
            face = ft2font.FT2Font(path)
            if all(face.get_char_index(ord(ch)) for ch in "数仓交易金额概念维度"):
                font_manager.fontManager.addfont(path)
                return font_manager.FontProperties(fname=path).get_name()
        except (OSError, RuntimeError):
            continue
    raise RuntimeError("未找到中文字体。请安装 Noto Sans CJK SC / 微软雅黑，或使用 --font 指定字体文件。")


def configure(font: str) -> None:
    plt.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": [font, "DejaVu Sans"],
        "axes.unicode_minus": False, "font.size": 13, "axes.labelsize": 13,
        "xtick.labelsize": 11, "ytick.labelsize": 13, "text.color": INK,
        "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": INK,
        "figure.facecolor": "white", "axes.facecolor": "white",
        "svg.fonttype": "none", "savefig.facecolor": "white",
    })


def save(fig, output: Path, name: str) -> None:
    for extension in ("png", "svg"):
        fig.savefig(output / f"{name}.{extension}", dpi=220, bbox_inches="tight", pad_inches=0.18)
    plt.close(fig)


def clean_axes(ax) -> None:
    for side in ["top", "right", "left"]:
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(axis="both", length=0, pad=8)
    ax.set_axisbelow(True)


def monthly_chart(data: dict, output: Path) -> None:
    records = sorted(data["monthly"], key=lambda r: r["period"])
    periods = [date.fromisoformat(r["period"][:10]) for r in records]
    values = [float(r["sales_amount"]) for r in records]
    source_start = date.fromisoformat(data["date_start"])
    source_end = date.fromisoformat(data["date_end"])
    complete = [
        source_start <= p and source_end >= date(p.year, p.month, calendar.monthrange(p.year, p.month)[1])
        for p in periods
    ]
    fig, ax = plt.subplots(figsize=(8.2, 4.9))
    fig.subplots_adjust(left=0.10, right=0.97, top=0.78, bottom=0.25)
    fig.text(0.10, 0.94, "月度正向交易金额", fontsize=20, fontweight="bold", color=NAVY)
    fig.text(0.10, 0.875, "以完整自然月比较趋势；末月仅覆盖 12 月 1—9 日", fontsize=12, color=MUTED)
    for index in range(len(periods) - 1):
        solid = complete[index] and complete[index + 1]
        ax.plot([index, index + 1], values[index:index + 2],
                color=TEAL if solid else "#9aaeb9", lw=2.6, ls="-" if solid else "--")
    for index, (amount, is_complete) in enumerate(zip(values, complete)):
        if not is_complete:
            ax.axvspan(index - 0.42, index + 0.42, color="#edf0f3", zorder=0)
        ax.scatter(index, amount, s=45, color=TEAL if is_complete else "#9aaeb9", zorder=3)
    peak = max((i for i, flag in enumerate(complete) if flag), key=lambda i: values[i])
    ax.annotate(f"完整月峰值\n£{values[peak]:,.0f}", xy=(peak, values[peak]),
                xytext=(max(0, peak - 3.5), max(values) * 1.01), fontsize=12,
                arrowprops={"arrowstyle": "-", "color": TEAL}, color=TEAL, ha="left")
    ax.set_xticks(range(len(periods)), [p.strftime("%Y-%m") for p in periods], rotation=45, ha="right")
    ax.set_ylim(0, max(values) * 1.28)
    ax.set_xlim(-0.3, len(periods) - 0.7)
    ax.set_ylabel("金额（百万 GBP）")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x / 1_000_000:.1f}"))
    ax.grid(axis="y", color=GRID, lw=0.8)
    clean_axes(ax)
    fig.text(0.10, 0.075, "浅灰背景与虚线表示不完整月；2010 年 12 月为完整月。", fontsize=11, color=MUTED)
    fig.text(0.10, 0.025, FOOTNOTE, fontsize=10.3, color=MUTED)
    save(fig, output, "monthly_amount")


def country_chart(data: dict, output: Path) -> None:
    records = sorted(data["countries"], key=lambda r: float(r["sales_amount"]), reverse=True)[:6]
    names = {"United Kingdom": "英国", "Netherlands": "荷兰", "EIRE": "爱尔兰 EIRE",
             "Germany": "德国", "France": "法国", "Australia": "澳大利亚"}
    total = float(data["overview"]["sales_amount"])
    fig, ax = plt.subplots(figsize=(8.2, 4.9))
    fig.subplots_adjust(left=0.19, right=0.96, top=0.75, bottom=0.26)
    fig.text(0.08, 0.94, "国家正向交易金额 Top 6", fontsize=20, fontweight="bold", color=NAVY)
    uk = next((r for r in records if r["country"] == "United Kingdom"), None)
    subtitle = f"英国占全部金额的 {float(uk['sales_amount']) / total:.1%}；横轴为对数刻度" if uk else "横轴为对数刻度，点旁标注实际金额"
    fig.text(0.08, 0.875, subtitle, fontsize=12, color=MUTED)
    ax.set_xscale("log")
    left = min(float(r["sales_amount"]) for r in records) / 2.0
    right = max(float(r["sales_amount"]) for r in records) * 3.1
    for i, record in enumerate(records):
        amount = float(record["sales_amount"])
        color = TEAL if record["country"] == "United Kingdom" else BLUE
        ax.hlines(i, left, amount, color=GRID, lw=2)
        ax.scatter(amount, i, s=80, color=color, zorder=3)
        ax.text(amount * 1.15, i, f"£{amount:,.0f}", ha="left", va="center", fontsize=12, color=color)
    ax.set_yticks(range(len(records)), [names.get(r["country"], r["country"]) for r in records])
    ax.invert_yaxis()
    ax.set_ylim(len(records) - 0.5, -0.5)
    ax.set_xlim(left, right)
    ax.set_xticks([100_000, 300_000, 1_000_000, 3_000_000, 10_000_000],
                  ["10万", "30万", "100万", "300万", "1000万"])
    ax.minorticks_off()
    ax.set_xlabel("正向交易金额（GBP，对数刻度）", labelpad=10)
    ax.grid(axis="x", color=GRID, lw=0.8)
    clean_axes(ax)
    fig.text(0.08, 0.075, "国家取自交易记录中的客户所在国家；没有将国家固定绑定到客户。", fontsize=10.8, color=MUTED)
    fig.text(0.08, 0.025, FOOTNOTE, fontsize=10.3, color=MUTED)
    save(fig, output, "country_top6")


def diagram_canvas(title: str, subtitle: str, height=6.1):
    fig, ax = plt.subplots(figsize=(8.2, height))
    fig.subplots_adjust(left=0.02, right=0.98, top=0.84, bottom=0.08)
    ax.set_xlim(-0.025, 1.025)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.text(0.04, 0.955, title, fontsize=20, fontweight="bold", color=NAVY)
    fig.text(0.04, 0.905, subtitle, fontsize=11.5, color=MUTED)
    return fig, ax


def box(ax, x, y, w, h, title, body, *, fill="white", title_color=NAVY, size=12, title_size=13):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.015",
                              facecolor=fill, edgecolor="#b8cbd6", linewidth=1.1, zorder=2))
    ax.text(x + w / 2, y + h - 0.035, title, ha="center", va="top",
            color=title_color, fontsize=title_size, fontweight="bold", zorder=3)
    if body:
        ax.text(x + w / 2, y + h / 2 - 0.035, body, ha="center", va="center",
                color=INK, fontsize=size, linespacing=1.55, zorder=3)


def arrow(ax, start, end, label=None, label_offset=(0, 0)):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=13,
                               linewidth=1.5, color="#7894a7", zorder=1))
    if label:
        x, y = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
        ax.text(x + label_offset[0], y + label_offset[1], label, ha="center", va="center",
                fontsize=10, color=MUTED, bbox={"facecolor": "white", "edgecolor": "none", "pad": 1})


def concept_chart(output: Path) -> None:
    fig, ax = diagram_canvas("概念设计：围绕销售交易分析", "一条事实对应一条来源交易记录；单据可包含多条商品或业务项目明细", height=5.8)
    box(ax, .35, .32, .30, .30, "交易明细", "单据编号 · 时间\n数量 · 单价 · 金额", fill=PALE, size=14, title_size=16)
    box(ax, .02, .66, .25, .24, "日期", "年 · 季度 · 月 · 日")
    box(ax, .73, .66, .25, .24, "商品与业务项目", "代码 · 名称")
    box(ax, .02, .09, .25, .24, "客户", "原始客户编号\n未知客户保留交易")
    box(ax, .73, .09, .25, .24, "国家", "交易记录中的\n客户所在国家")
    arrow(ax, (.27, .72), (.35, .57), "1 : N", (-.02, .025))
    arrow(ax, (.73, .72), (.65, .57), "1 : N", (.02, .025))
    arrow(ax, (.27, .24), (.35, .37), "1 : N", (-.025, -.025))
    arrow(ax, (.73, .24), (.65, .37), "1 : N", (.025, -.025))
    fig.text(.04, .025, "单据编号是退化维度；单据编号与商品代码的组合不假定唯一。", fontsize=11, color=MUTED)
    save(fig, output, "concept_model")


def star_chart(output: Path) -> None:
    fig, ax = diagram_canvas("逻辑设计：四维星型模型", "PK 主键；FK 逻辑外键；所有维度均有 key = 0 的未知成员", height=6.2)
    box(ax, .32, .12, .36, .78, "dwd.fact_transaction",
        "PK source_row_number\ninvoice_no · invoice_ts\nFK date_key\nFK product_key\nFK customer_key\nFK country_key\nquantity · unit_price\nline_amount\n三类质量与交易标记", fill=PALE, size=11.5, title_size=12.5)
    box(ax, .01, .65, .25, .24, "dim.date", "PK date_key\nfull_date\nyear / quarter / month / day", size=10.5, title_size=12)
    box(ax, .74, .65, .25, .24, "dim.product", "PK product_key\nstock_code\ndescription", size=11.2, title_size=12)
    box(ax, .01, .16, .25, .23, "dim.customer", "PK customer_key\ncustomer_id", size=11.2, title_size=12)
    box(ax, .74, .16, .25, .23, "dim.country", "PK country_key\ncountry", size=11.2, title_size=12)
    arrow(ax, (.26, .75), (.32, .70))
    arrow(ax, (.74, .75), (.68, .65))
    arrow(ax, (.26, .27), (.32, .55))
    arrow(ax, (.74, .27), (.68, .50))
    fig.text(.04, .025, "粒度：来源交易明细行。金额采用 DECIMAL；全部来源行保留，可追溯至原始 Excel。", fontsize=10.5, color=MUTED)
    save(fig, output, "star_schema")


def architecture_chart(output: Path) -> None:
    fig, ax = diagram_canvas("系统架构：离线分层计算与分析", "Python 负责导入与编排，DuckDB SQL 负责分层计算，Streamlit 展示结果", height=6.8)
    center_x, width, height = .43, .53, .092
    steps = [
        (.875, "真实源数据", "UCI Online Retail.xlsx"),
        (.745, "ODS 原始层", "原始字段 + 来源行号 + 文件哈希"),
        (.615, "STG 清洗层", "类型规范 · 取消与异常标记"),
        (.485, "DWD 交易明细层", "关联四个维度，保留全部来源行"),
        (.355, "DWS 主题汇总层", "日国家 · 日商品国家 · 日客户国家"),
        (.225, "ADS 应用层", "稳定查询接口 + 跨期订单与客户去重"),
        (.095, "Streamlit 分析看板", "概览 · 商品与业务项目 · 国家与客户"),
    ]
    for i, (y, title, body) in enumerate(steps):
        box(ax, center_x, y, width, height, "", None, fill=PALE if i in (3, 5, 6) else "white", title_size=12)
        ax.text(center_x + width / 2, y + .068, title, fontsize=12, ha="center", va="center",
                fontweight="bold", color=NAVY, zorder=3)
        ax.text(center_x + width / 2, y + .022, body, fontsize=10.6, ha="center", va="center", zorder=3)
        if i:
            previous_y = steps[i - 1][0]
            arrow(ax, (center_x + width / 2, previous_y - .012), (center_x + width / 2, y + height + .012))
    box(ax, .025, .44, .30, .18, "DIM 共享维度", "日期 · 商品/业务项目\n客户 · 国家", fill="#edf4f8", size=11.8)
    arrow(ax, (.325, .53), (.43, .53), "关联", (0, .025))
    ax.text(.17, .88, "本地离线全量重建", ha="center", fontsize=12, color=TEAL, fontweight="bold")
    ax.text(.17, .81, "真实数据可追溯\n分层结果可复核\n统一指标口径", ha="center", va="top", fontsize=12, color=MUTED, linespacing=1.7)
    ax.text(.17, .30, "验证通过后发布数据库\n构建失败保留旧库", ha="center", va="top", fontsize=11.8, color=MUTED, linespacing=1.7)
    fig.text(.04, .025, "主流程：ODS → STG → DWD → DWS → ADS；DIM 为共享维度层。", fontsize=11, color=MUTED)
    save(fig, output, "layer_architecture")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis", type=Path, default=ROOT / "data/exports/analysis.json")
    parser.add_argument("--output", type=Path, default=ROOT / "assets/report_figures")
    parser.add_argument("--font", type=Path, default=None)
    args = parser.parse_args()
    data = json.loads(args.analysis.read_text(encoding="utf-8"))
    if not data.get("monthly") or not data.get("countries"):
        raise ValueError("analysis.json 缺少月度或国家真实分析结果，请先运行 pipeline.py。")
    font = select_font(args.font)
    configure(font)
    args.output.mkdir(parents=True, exist_ok=True)
    monthly_chart(data, args.output)
    country_chart(data, args.output)
    concept_chart(args.output)
    star_chart(args.output)
    architecture_chart(args.output)
    print(f"已生成5组 PNG/SVG 图，字体：{font}，目录：{args.output}")


if __name__ == "__main__":
    main()
