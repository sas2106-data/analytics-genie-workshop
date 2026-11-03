# Databricks notebook source
# MAGIC %md
# MAGIC # Module 3 · Build the AI/BI dashboard (50 min)
# MAGIC
# MAGIC **Goal:** a published, shareable *Policy Overview* dashboard on the diamond table and the certified metric view.
# MAGIC
# MAGIC | Step | Time | What you do |
# MAGIC |---|---|---|
# MAGIC | 1 | 5 min | Create the dashboard and add two datasets |
# MAGIC | 2 | 25 min | Build the visuals |
# MAGIC | 3 | 5 min | Add filters |
# MAGIC | 4 | 7 min | Parameter exercise |
# MAGIC | 5 | 5 min | Publish and share |
# MAGIC | 6 | 3 min | Check: the counters match the certified table |
# MAGIC
# MAGIC **Prerequisite:** Modules 1 and 2 are done. Most of this module is in the dashboard editor; this notebook gives you
# MAGIC the exact SQL to paste and a **catch-up cell** that builds the finished dashboard for you.

# COMMAND ----------

# MAGIC %pip install -q --upgrade "databricks-sdk>=0.60"

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %run ./_config

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1 · Create the dashboard and add two datasets
# MAGIC 1. Open **Dashboards → Create dashboard**. Rename it to the name printed below.
# MAGIC 2. Open the **Data** tab → **Create from SQL**, and paste dataset **Policies (diamond)** from the next cell's output.
# MAGIC    It powers the interactive visuals and filters.
# MAGIC 3. **Add data → choose `policy_metrics`** (the metric view), or **Create from SQL** with dataset **Certified metrics**.

# COMMAND ----------

policies_sql = f"""SELECT policy_number, product_line, policy_status, issue_date,
       CAST(date_trunc('month', issue_date) AS DATE) AS issue_month,
       CASE WHEN policy_status = 'In force' THEN 1 ELSE 0 END AS is_in_force, premium_amount
FROM {diamond}"""
certified_sql = f"""SELECT product_line, policy_status,
       MEASURE(total_policies) AS total_policies, MEASURE(in_force_policies) AS in_force_policies,
       MEASURE(in_force_rate) AS in_force_rate, MEASURE(total_premium) AS total_premium,
       MEASURE(avg_premium) AS avg_premium
FROM {metrics}
GROUP BY ALL"""
print(f"Dashboard name: {dashboard_name}\n\n-- Dataset 'Policies (diamond)'\n{policies_sql}\n\n-- Dataset 'Certified metrics'\n{certified_sql}")
display(spark.sql(policies_sql).limit(5))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2 · Build the visuals
# MAGIC On the **Canvas**, click **Add a visualization** for each row. Pick the dataset, the type, then the fields.
# MAGIC
# MAGIC | Visual | Dataset | Fields |
# MAGIC |---|---|---|
# MAGIC | Counter: Total policies | Policies | `COUNT(policy_number)` |
# MAGIC | Counter: In-force policies | Policies | `SUM(is_in_force)` |
# MAGIC | Counter: In-force rate | Policies | `AVG(is_in_force)`, format **Percent** |
# MAGIC | Counter: Total premium | Policies | `SUM(premium_amount)`, format **Currency** |
# MAGIC | Line: policies issued per month | Policies | X `issue_month`, Y `COUNT(policy_number)`, colour `product_line` |
# MAGIC | Bar: policies by status | Policies | `policy_status` × `COUNT(policy_number)` |
# MAGIC | Bar: total premium | Policies | `product_line` × `SUM(premium_amount)` |
# MAGIC | Bar: average premium | Policies | `product_line` × `AVG(premium_amount)` |
# MAGIC | Table: certified metrics | Certified metrics | all columns |
# MAGIC
# MAGIC Tip: type what you want in the **Ask Assistant** box on a widget (for example "monthly policies by product line")
# MAGIC and let it pick the fields.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3 · Add filters
# MAGIC Add two **Multiple values** filters, `product_line` and `policy_status`. In each filter's **Fields**, connect it to
# MAGIC **both** datasets, so the counters, the charts and the certified table all respond.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4 · Parameter exercise
# MAGIC 1. In **Data**, clone *Policies (diamond)* and add `WHERE issue_date >= :from_date` at the end.
# MAGIC 2. Set the parameter type to **Date**, default one year ago.
# MAGIC 3. On the canvas, add a **Date picker** filter connected to the `from_date` parameter.
# MAGIC 4. Point the line chart at the cloned dataset and change the date.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5 · Publish and share
# MAGIC 1. Click **Publish**. Turn **Embed credentials** *off*, so viewers query with **their own** permissions (Module 5).
# MAGIC 2. Click **Share** and give your group **Can run**.
# MAGIC 3. Copy the link.
# MAGIC
# MAGIC ### Catch-up cell
# MAGIC Run the next cell to build the finished dashboard from `dashboards/policy_overview.lvdash.json` (the answer key)
# MAGIC and publish it without embedded credentials.

# COMMAND ----------

import base64
from databricks.sdk.service.dashboards import Dashboard
from databricks.sdk.service.workspace import ExportFormat

dash_path = f"{repo_root}/dashboards/policy_overview.lvdash.json"
try:
    spec = json.load(open(dash_path))
except Exception:   # in Git folders, .lvdash.json files are dashboard objects: read them through the export API
    spec = json.loads(base64.b64decode(
        w.workspace.export(dash_path.removeprefix("/Workspace"), format=ExportFormat.SOURCE).content))
for ds in spec["datasets"]:   # the file uses unqualified table names; point them at your target schema
    ds["catalog"], ds["schema"] = target_catalog, target_schema

body = Dashboard(display_name=dashboard_name, warehouse_id=warehouse_id,
                 serialized_dashboard=json.dumps(spec), parent_path=os.path.dirname(nb_path))
dashboard_id = find_dashboard_id()
if dashboard_id:
    w.lakeview.update(dashboard_id, dashboard=body)
else:
    dashboard_id = w.lakeview.create(dashboard=body).dashboard_id
w.lakeview.publish(dashboard_id, embed_credentials=False, warehouse_id=warehouse_id)
print(f"✅ Dashboard: {w.config.host}/dashboardsv3/{dashboard_id}/published")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6 · Check: same numbers, one definition
# MAGIC With no filters set, the **counters** (computed from the diamond table) must match the **certified table**
# MAGIC (computed by the metric view). This cell does the same comparison:

# COMMAND ----------

display(spark.sql(f"""
  SELECT 'diamond (counters)' AS computed_from, count(*) AS total_policies,
         sum(CASE WHEN policy_status = 'In force' THEN 1 ELSE 0 END) AS in_force_policies, sum(premium_amount) AS total_premium
  FROM {diamond}
  UNION ALL
  SELECT 'metric view (certified table)', MEASURE(total_policies), MEASURE(in_force_policies), MEASURE(total_premium)
  FROM {metrics}"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ✅ **Module 3 done.** Next: `04_Genie_Agent`.
