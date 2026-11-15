{% docs __overview__ %}
# 在线零售销售分析数仓
Python接入UCI原始Excel。dbt通过source与ref组织ODS、STG、DIM、DWD、DWS和ADS依赖。
销售与取消事实共享四个维度，以来源行号追溯原始记录。取消没有逐笔原单关联，净交易记录金额表示同窗口的带符号金额合计。
ADS包含指标总览、应用明细、日汇总、月份国家交易类型CUBE和年月层级ROLLUP。使用GROUPING标志选择汇总层级。
{% enddocs %}
