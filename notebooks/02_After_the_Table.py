# Databricks notebook source
# MAGIC %md
# MAGIC # Module 2 · What happens after you've built a table you like (35 min)
# MAGIC
# MAGIC **Goal:** make `policy_diamond` something others can find, trust and reuse, **before** anyone builds a report on it.
# MAGIC
# MAGIC | Step | Time | What you do |
# MAGIC |---|---|---|
# MAGIC | 1 | 8 min | Documentation: table and column comments, AI-generated descriptions |
# MAGIC | 2 | 7 min | Lineage: source → ruby → diamond |
# MAGIC | 3 | 5 min | Data quality: what the pipeline's expectations caught |
# MAGIC | 4 | 10 min | Certified metrics: create the metric view `policy_metrics` and query it |
# MAGIC | 5 | 5 min | Certify it and find it in Catalog Explorer |
# MAGIC
# MAGIC **Prerequisite:** Module 1 is done (the pipeline has run). Use the same widget values as before.

# COMMAND ----------

# MAGIC %run ./_config

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1 · Documentation (UI + code)
# MAGIC 1. Open **Catalog** in the left sidebar, then go to your target schema → `policy_diamond`.
# MAGIC 2. **Overview tab:** the table and column comments came from the pipeline SQL, so nobody had to type them twice.
# MAGIC 3. On `policy_ruby`, click **AI generate** next to a description to see a suggested comment. Accept or edit it.
# MAGIC 4. **Details tab:** owner, the pipeline that maintains the table, last refresh.
# MAGIC
# MAGIC The same comments are queryable:

# COMMAND ----------

display(spark.sql(f"""
  SELECT table_name, column_name, data_type, comment
  FROM `{target_catalog}`.information_schema.columns
  WHERE table_schema = '{target_schema}' AND table_name = 'policy_diamond'
  ORDER BY ordinal_position"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2 · Lineage (UI)
# MAGIC On `policy_diamond`, open the **Lineage** tab → **See lineage graph**:
# MAGIC - upstream: `policy_ruby` ← `annuity_policy`, `life_policy`;
# MAGIC - click a column, such as `premium_amount`, to see **column-level** lineage back to `single_premium` and `annual_premium`;
# MAGIC - after Modules 3 and 4, the dashboard and Genie Agent show up **downstream** too.
# MAGIC
# MAGIC Lineage is also in system tables (it can take a few minutes to appear):

# COMMAND ----------

try:
    display(spark.sql(f"""
      SELECT DISTINCT source_table_full_name, target_table_full_name
      FROM system.access.table_lineage
      WHERE target_table_catalog = '{target_catalog}' AND target_table_schema = '{target_schema}'
        AND source_table_full_name IS NOT NULL
      ORDER BY target_table_full_name"""))
except Exception as e:
    print("system.access.table_lineage isn't available to you; use the Lineage tab instead.", str(e).splitlines()[0][:120])

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3 · Data quality (UI + code)
# MAGIC In the pipeline, click `policy_ruby` → **Data quality**. Each expectation shows rows passed and failed.
# MAGIC The same numbers come from the pipeline's event log:

# COMMAND ----------

pipeline_id = find_pipeline_id()
assert pipeline_id, f"Pipeline '{pipeline_name}' not found. Run Module 1 first."
display(spark.sql(f"""
  WITH latest AS (SELECT max_by(origin.update_id, timestamp) AS update_id
                  FROM event_log('{pipeline_id}') WHERE event_type = 'flow_progress')
  SELECT element_at(split(origin.flow_name, '[.]'), -1) AS table_name, e.name AS expectation, e.passed_records, e.failed_records
  FROM event_log('{pipeline_id}')
  LATERAL VIEW explode(from_json(details:flow_progress:data_quality:expectations,
                       'array<struct<name:string,dataset:string,passed_records:bigint,failed_records:bigint>>')) x AS e
  WHERE event_type = 'flow_progress' AND details:flow_progress:data_quality IS NOT NULL
    AND origin.update_id = (SELECT update_id FROM latest)
  ORDER BY table_name, expectation"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4 · Certified metrics: the metric view `policy_metrics`
# MAGIC If "in-force rate" is computed in each chart or each Genie answer, the numbers drift. A **metric view** defines the
# MAGIC measures **once** in Unity Catalog, on top of the diamond table; the dashboard, Genie and SQL all reuse them.
# MAGIC
# MAGIC | Measure | Definition |
# MAGIC |---|---|
# MAGIC | `total_policies` | `COUNT(1)` |
# MAGIC | `in_force_policies` | status *In force* |
# MAGIC | `in_force_rate` | in-force policies ÷ all policies |
# MAGIC | `total_premium` | `SUM(premium_amount)` |
# MAGIC | `avg_premium` | `AVG(premium_amount)` |
# MAGIC
# MAGIC Dimensions: `product_line`, `policy_status`, `issue_year`, `issue_month`, each with display names and synonyms that
# MAGIC Genie uses. (The same statement is in `sql/02_metric_view.sql` for the SQL Editor.)

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE VIEW {metrics}
WITH METRICS LANGUAGE YAML
COMMENT 'Certified policy KPIs: policy counts, in-force rate and premium by product line, status and issue period.'
AS $$
version: 1.1
source: {target_catalog}.{target_schema}.policy_diamond
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
print(f"Created {metrics}")

# COMMAND ----------

# MAGIC %md
# MAGIC Query it. Every measure is wrapped in `MEASURE()`; dimensions are not. Try changing the `GROUP BY` to `issue_year`.

# COMMAND ----------

display(spark.sql(f"""
  SELECT product_line,
         MEASURE(total_policies)                 AS total_policies,
         MEASURE(in_force_policies)              AS in_force_policies,
         ROUND(100 * MEASURE(in_force_rate), 1)  AS in_force_pct,
         ROUND(MEASURE(total_premium))           AS total_premium
  FROM {metrics}
  GROUP BY ALL
  ORDER BY product_line"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5 · Certify it
# MAGIC Tag the metric view as certified, then find it in **Catalog**: it now shows a **Certified** badge, so report
# MAGIC developers and Genie users know which definitions to trust. This needs `ASSIGN` on the `system.certification_status`
# MAGIC governed tag. If you don't have it, skip this step.

# COMMAND ----------

try:
    spark.sql(f"ALTER VIEW {metrics} SET TAGS ('system.certification_status' = 'certified')")
    print("✅ Tagged as certified")
except Exception as e:
    print("Skipped: needs ASSIGN on system.certification_status →", str(e).splitlines()[0][:150])

# COMMAND ----------

# MAGIC %md
# MAGIC ✅ **Module 2 done.** You have a documented, lineage-tracked, quality-checked diamond table and one certified set of
# MAGIC measures on it. Next: `03_AIBI_Dashboard`.
