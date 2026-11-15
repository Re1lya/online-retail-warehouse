"""运行时核对真实数据的行数、关联完整性与汇总金额，不通过则终止发布。"""
def validate(con):
    checks = []
    def check(name, actual, expected):
        checks.append({"name": name,"actual":str(actual),"expected":str(expected),"passed":actual==expected})
    scalar=lambda q: con.execute(q).fetchone()[0]
    raw=scalar("SELECT COUNT(*) FROM ods.retail_raw")
    check("ODS与DWD行数守恒",scalar("SELECT COUNT(*) FROM dwd.fact_transaction"),raw)
    check("事实表来源行号唯一",scalar("SELECT COUNT(DISTINCT source_row_number) FROM dwd.fact_transaction"),raw)
    for dim,key in [("date","date_key"),("product","product_key"),("customer","customer_key"),("country","country_key")]:
        check(f"{dim}维度关联完整",scalar(f"SELECT COUNT(*) FROM dwd.fact_transaction f LEFT JOIN dim.{dim} d USING({key}) WHERE d.{key} IS NULL"),0)
    expected=scalar("SELECT SUM(quantity * unit_price) FROM stg.clean_transactions WHERE is_positive_sale")
    check("DWD正向销售额",scalar("SELECT SUM(line_amount) FROM dwd.fact_transaction WHERE is_positive_sale"),expected)
    for table in ["dws.sales_day_country","dws.product_day_country"]:
        check(f"{table}金额守恒",scalar(f"SELECT SUM(sales_amount) FROM {table}"),expected)
    known=scalar("SELECT SUM(line_amount) FROM dwd.fact_transaction WHERE is_positive_sale AND customer_key<>0")
    check("已知客户汇总金额守恒",scalar("SELECT SUM(sales_amount) FROM dws.customer_day_country"),known)
    check("取消记录未计入正向销售",scalar("SELECT COUNT(*) FROM ads.sales_detail WHERE is_cancelled"),0)
    check("正向销售明细金额均为正",scalar("SELECT COUNT(*) FROM ads.sales_detail WHERE line_amount<=0 OR line_amount IS NULL"),0)
    check("ADS与STG正向记录数相同",scalar("SELECT COUNT(*) FROM ads.sales_detail"),scalar("SELECT COUNT(*) FROM stg.clean_transactions WHERE is_positive_sale"))
    return {"passed":all(c["passed"] for c in checks),"checks":checks}
