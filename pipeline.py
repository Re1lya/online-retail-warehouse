"""python pipeline.py：全量重建本项目数据库；构建/校验/导出准备失败保留旧库。"""
import argparse
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import time
import tempfile
from zoneinfo import ZoneInfo
import duckdb
from src.ingest import load_ods
from src.quality import quality_report
from src.validation import validate
from src import analytics

ROOT=Path(__file__).resolve().parent

def json_value(x):
    if isinstance(x,Decimal): return str(x)
    if hasattr(x,"isoformat"): return x.isoformat()
    if hasattr(x,"item"): return x.item()
    raise TypeError(type(x).__name__)

def write_json(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,default=json_value),encoding="utf-8")

def run(source, db):
    started=time.perf_counter()
    db.parent.mkdir(parents=True,exist_ok=True)
    exports=ROOT/"data/exports"; exports.mkdir(parents=True,exist_ok=True)
    temp=db.with_suffix(".building.duckdb")
    if temp.exists(): temp.unlink()
    con=duckdb.connect(str(temp))
    try:
        print("[1/5] 读取真实数据并导入ODS",flush=True)
        ingest=load_ods(con,source)
        for i,sql in enumerate(["10_clean.sql","20_model.sql","30_marts.sql"],2):
            print(f"[{i}/5] 执行 {sql}",flush=True)
            con.execute((ROOT/"sql"/sql).read_text(encoding="utf-8"))
        quality=quality_report(con)
        validation=validate(con)
        if not validation["passed"]:
            write_json(exports/"validation_failed.json",validation)
            raise RuntimeError("数据校验失败，查看data/exports/validation_failed.json；旧库未替换")
        first,last=analytics.bounds(con)
        overview=analytics.overview(con,first,last)
        results={
            "date_start":first,"date_end":last,"currency":"GBP","metric_basis":"positive_sales_including_flagged_duplicates",
            "overview":overview,
            "monthly":analytics.trend(con,first,last).to_dict("records"),
            "products":analytics.products(con,first,last).to_dict("records"),
            "countries":analytics.country_ranking(con,first,last).to_dict("records"),
            "customers":analytics.customers(con,first,last).to_dict("records"),
        }
        inventory=con.execute("""SELECT table_schema, table_name, table_type FROM information_schema.tables
          WHERE table_schema IN ('ods','stg','dim','dwd','dws','ads') ORDER BY table_schema,table_name""").fetchdf()
        inventory["row_count"]=[con.execute(f'SELECT COUNT(*) FROM "{r.table_schema}"."{r.table_name}"').fetchone()[0] for r in inventory.itertuples()]
        metadata={"built_at":datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),"elapsed_seconds":round(time.perf_counter()-started,2),
          "source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),"ingest":ingest,"duckdb_version":duckdb.__version__,"tables":inventory.to_dict("records")}
        con.execute("CHECKPOINT")
        con.close();con=None
        # 先准备所有导出，避免序列化或CSV生成失败时已经替换旧库。
        # 数据库文件替换是原子的；数据库与多个导出文件不构成跨文件事务。
        with tempfile.TemporaryDirectory(prefix=".export-",dir=exports) as staging_dir:
            staging=Path(staging_dir)
            write_json(staging/"quality.json",quality)
            write_json(staging/"validation.json",validation)
            write_json(staging/"analysis.json",results)
            write_json(staging/"build.json",metadata)
            inventory.to_csv(staging/"table_inventory.csv",index=False,encoding="utf-8-sig")
            import pandas as pd
            for key in ["monthly","products","countries","customers"]:
                pd.DataFrame(results[key]).to_csv(staging/f"{key}.csv",index=False,encoding="utf-8-sig")
            temp.replace(db)
            for file in staging.iterdir(): file.replace(exports/file.name)
        print("[5/5] 校验通过，数据库与分析结果已生成",flush=True)
        print(json.dumps(overview,ensure_ascii=False,default=json_value))
        return results
    finally:
        if con is not None: con.close()
        if temp.exists(): temp.unlink()

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,default=ROOT/"data/raw/Online Retail.xlsx")
    p.add_argument("--db",type=Path,default=ROOT/"data/warehouse/retail.duckdb")
    args=p.parse_args()
    if not args.source.exists():
        p.error("缺少真实数据。先运行 python -m src.download_data，再运行流水线。")
    run(args.source.resolve(),args.db.resolve())
