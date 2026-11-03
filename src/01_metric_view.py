# Databricks notebook source
# MAGIC %md
# MAGIC # 01 · Certified metrics: metric view `policy_metrics`
# MAGIC Business measures defined **once** in Unity Catalog, on top of the diamond table. The dashboard and Genie both use
# MAGIC these definitions, so a chart and a plain-language question return the same numbers.

# COMMAND ----------

dbutils.widgets.text("target_catalog", "main")
dbutils.widgets.text("target_schema", "policy_layers")

catalog = dbutils.widgets.get("target_catalog")
schema = dbutils.widgets.get("target_schema")
mv = f"`{catalog}`.`{schema}`.policy_metrics"

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE VIEW {mv}
WITH METRICS LANGUAGE YAML
COMMENT 'Certified policy KPIs: policy counts, in-force rate and premium by product line, status and issue period.'
AS $$
version: 1.1
source: {catalog}.{schema}.policy_diamond
fields:
  - name: product_line
    expr: product_line
    display_name: Product Line
    synonyms: [line of business, LOB, product]
  - name: policy_status
    expr: policy_status
    display_name: Policy Status
    synonyms: [status]
  - name: issue_year
    expr: YEAR(issue_date)
    display_name: Issue Year
    synonyms: [year]
  - name: issue_month
    expr: DATE_TRUNC('MONTH', issue_date)
    display_name: Issue Month
    synonyms: [month, period]
measures:
  - name: total_policies
    expr: COUNT(1)
    display_name: Total Policies
    synonyms: [policies, policy count, number of policies, contracts]
  - name: in_force_policies
    expr: SUM(CASE WHEN policy_status = 'In force' THEN 1 ELSE 0 END)
    display_name: In-force Policies
    comment: Policies with status In force (active).
    synonyms: [in force, active policies, inforce]
  - name: in_force_rate
    expr: AVG(CASE WHEN policy_status = 'In force' THEN 1.0 ELSE 0.0 END)
    display_name: In-force Rate
    comment: Share of policies that are still in force.
    synonyms: [persistency, retention rate]
  - name: total_premium
    expr: SUM(premium_amount)
    display_name: Total Premium
    comment: Annuity single premium plus life annualised premium, USD.
    synonyms: [premium, written premium, sales]
  - name: avg_premium
    expr: AVG(premium_amount)
    display_name: Average Premium
    synonyms: [average premium, premium per policy]
$$
""")

# Mark the metric view as certified (needs ASSIGN on the system.certification_status governed tag)
try:
    spark.sql(f"ALTER VIEW {mv} SET TAGS ('system.certification_status' = 'certified')")
    print("Tagged as certified")
except Exception as e:
    print("Could not tag as certified (needs ASSIGN on system.certification_status):", str(e).splitlines()[0][:150])

display(spark.sql(f"""SELECT product_line, MEASURE(total_policies) AS total_policies,
                             MEASURE(in_force_policies) AS in_force_policies,
                             ROUND(100 * MEASURE(in_force_rate), 1) AS in_force_pct,
                             ROUND(MEASURE(total_premium)) AS total_premium
                      FROM {mv} GROUP BY ALL ORDER BY product_line"""))
