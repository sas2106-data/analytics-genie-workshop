# Databricks notebook source
# MAGIC %md
# MAGIC # 02 · Certified metrics — metric view `case_metrics`
# MAGIC Business measures defined **once** in Unity Catalog. The dashboard and Genie both use these definitions,
# MAGIC so a chart and a plain-language question return the same numbers.

# COMMAND ----------

dbutils.widgets.text("catalog", "main")
dbutils.widgets.text("schema", "analytics_src")
dbutils.widgets.text("target_schema", "")

catalog = dbutils.widgets.get("catalog")
target = dbutils.widgets.get("target_schema").strip() or dbutils.widgets.get("schema")
mv = f"`{catalog}`.`{target}`.case_metrics"

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE VIEW {mv}
WITH METRICS LANGUAGE YAML
COMMENT 'Certified case KPIs: volumes, open cases, days to close and SLA attainment by customer and case attributes.'
AS $$
version: 1.1
source: {catalog}.{target}.case_customer
fields:
  - name: opened_month
    expr: opened_month
    display_name: Opened Month
    synonyms: [month, period]
  - name: case_type
    expr: case_type
    display_name: Case Type
    synonyms: [type, category]
  - name: channel
    expr: channel
    display_name: Channel
  - name: priority
    expr: priority
    display_name: Priority
  - name: status
    expr: status
    display_name: Status
  - name: segment
    expr: segment
    display_name: Customer Segment
    synonyms: [segment, customer type]
  - name: region
    expr: region
    display_name: Region
  - name: is_vip
    expr: is_vip
    display_name: VIP Customer
measures:
  - name: total_cases
    expr: COUNT(1)
    display_name: Total Cases
    synonyms: [cases, case volume, number of cases]
  - name: open_cases
    expr: SUM(CASE WHEN is_open THEN 1 ELSE 0 END)
    display_name: Open Cases
    comment: Cases not yet closed (status open or pending).
    synonyms: [open, backlog, outstanding cases]
  - name: closed_cases
    expr: SUM(CASE WHEN is_open THEN 0 ELSE 1 END)
    display_name: Closed Cases
  - name: avg_days_to_close
    expr: AVG(days_to_close)
    display_name: Avg Days to Close
    comment: Average days from opened to closed, closed cases only.
    synonyms: [days to close, resolution time, time to close, average handling time]
  - name: sla_met_rate
    expr: AVG(CASE WHEN within_sla THEN 1.0 WHEN NOT within_sla THEN 0.0 END)
    display_name: SLA Met Rate
    comment: Share of closed cases closed within the SLA for their priority (high 2, medium 5, low 10 days).
    synonyms: [SLA, SLA attainment, on-time rate]
  - name: customers_with_cases
    expr: COUNT(DISTINCT customer_id)
    display_name: Customers with Cases
  - name: cases_per_customer
    expr: COUNT(1) / COUNT(DISTINCT customer_id)
    display_name: Cases per Customer
$$
""")

# Mark the metric view as certified (needs ASSIGN on the system.certification_status governed tag)
try:
    spark.sql(f"ALTER VIEW {mv} SET TAGS ('system.certification_status' = 'certified')")
    print("Tagged as certified")
except Exception as e:
    print("Could not tag as certified (needs ASSIGN on system.certification_status):", str(e).splitlines()[0][:150])

display(spark.sql(f"""SELECT segment, MEASURE(total_cases) AS total_cases, MEASURE(open_cases) AS open_cases,
                             ROUND(MEASURE(avg_days_to_close), 1) AS avg_days_to_close,
                             ROUND(100 * MEASURE(sla_met_rate), 1) AS sla_met_pct
                      FROM {mv} GROUP BY ALL ORDER BY total_cases DESC"""))
