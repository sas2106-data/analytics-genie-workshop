# Databricks notebook source
# MAGIC %md
# MAGIC # Two Tables → Ruby → Diamond → Certified Metrics → Dashboard + Genie: guided, executable steps
# MAGIC
# MAGIC Run top to bottom on **serverless** compute from the workshop Git folder. Each module does in code what the
# MAGIC facilitator shows in the UI (Lakeflow Pipelines Editor, Catalog Explorer, dashboard editor, Genie), so attendees can
# MAGIC catch up or re-run any step.
# MAGIC
# MAGIC | Module | What this notebook does |
# MAGIC |---|---|
# MAGIC | 1 · Layered architecture & pipeline | Checks `annuity_policy` and `life_policy` (or creates synthetic ones), then creates and runs the Lakeflow pipeline `pipeline/policy_layers.sql`: **ruby** = both tables unioned and standardised, **diamond** = 5 reporting columns |
# MAGIC | 2 · After the table: certify & document | Shows data-quality results and lineage, then creates the certified metric view `policy_metrics` on the diamond table |
# MAGIC | 3 · AI/BI dashboard | Creates and publishes the *Policy Overview* dashboard from `dashboards/policy_overview.lvdash.json` |
# MAGIC | 4 · Genie | Creates a Genie Agent on the diamond table and metric view, and asks it a question |
# MAGIC | 5 · Governance & sharing | Unity Catalog grants, dashboard `CAN RUN` and Genie `CAN RUN` for a group |
# MAGIC
# MAGIC Every resource gets your user name as a suffix, so attendees don't collide.

# COMMAND ----------

# The Genie, Lakeview and Pipelines APIs need a recent Databricks SDK (older serverless images ship an older one)
%pip install -q --upgrade "databricks-sdk>=0.60"
dbutils.library.restartPython()

# COMMAND ----------

dbutils.widgets.text("source_catalog", "main", "1 · Source catalog")
dbutils.widgets.text("source_schema", "policy_src", "2 · Source schema")
dbutils.widgets.text("annuity_table", "annuity_policy", "3 · Annuity table")
dbutils.widgets.text("life_table", "life_policy", "4 · Life table")
dbutils.widgets.text("target_catalog", "", "5 · Target catalog (blank = source catalog)")
dbutils.widgets.text("target_schema", "", "6 · Target schema (blank = policy_layers_<you>)")
dbutils.widgets.dropdown("create_sample_data", "false", ["false", "true"], "7 · Synthetic data if missing")
dbutils.widgets.text("warehouse_id", "", "8 · SQL warehouse ID (blank = first serverless)")
dbutils.widgets.text("group_name", "workshop-users", "9 · Account-level group that gets access")
dbutils.widgets.dropdown("cleanup", "no", ["no", "yes"], "10 · Delete resources at the end")

# COMMAND ----------

import json, os, re
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.dashboards import Dashboard
from databricks.sdk.service.pipelines import PipelineLibrary, FileLibrary

w = WorkspaceClient()
me = w.current_user.me().user_name
suffix = re.sub(r"[^a-z0-9]", "-", me.split("@")[0].lower())[:16].strip("-")

source_catalog = dbutils.widgets.get("source_catalog")
source_schema = dbutils.widgets.get("source_schema")
annuity_table = dbutils.widgets.get("annuity_table")
life_table = dbutils.widgets.get("life_table")
target_catalog = dbutils.widgets.get("target_catalog").strip() or source_catalog
target_schema = dbutils.widgets.get("target_schema").strip() or f'policy_layers_{suffix.replace("-", "_")}'
warehouse_id = dbutils.widgets.get("warehouse_id").strip() or next(
    (wh.id for wh in w.warehouses.list() if wh.enable_serverless_compute), None)
group_name = dbutils.widgets.get("group_name").strip()

nb_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
root = os.path.dirname(os.path.dirname(nb_path))
root = root if root.startswith("/Workspace") else f"/Workspace{root}"
src = f"{root}/src"
tgt = f"`{target_catalog}`.`{target_schema}`"

pipeline_name = f"Policy layers ({suffix})"
dashboard_name = f"Policy Overview ({suffix})"
genie_title = f"Policies — Genie ({suffix})"
print(f"user={me}\nsource={source_catalog}.{source_schema}.{{{annuity_table},{life_table}}}\n"
      f"target={target_catalog}.{target_schema}\nwarehouse={warehouse_id}\nrepo root={root}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Module 1 · Layered architecture & the pipeline
# MAGIC
# MAGIC | Layer | Table | What happens |
# MAGIC |---|---|---|
# MAGIC | Source | `annuity_policy`, `life_policy` | Already sourced. Same business entity, different column names and status values |
# MAGIC | **Ruby** | `policy_ruby` | The two tables **unioned** into one conformed table: mapped column names, `product_line`, standardised status, expectations drop rows with no policy number |
# MAGIC | **Diamond** | `policy_diamond` | Pared down to the **5 columns** reporting needs: `policy_number`, `product_line`, `policy_status`, `issue_date`, `premium_amount` |
# MAGIC
# MAGIC Both layers are defined in one file, `pipeline/policy_layers.sql`, and run as a **Lakeflow Spark Declarative Pipeline**
# MAGIC on serverless. The pipeline works out the order (ruby before diamond) from the SQL.
# MAGIC In the UI: **Jobs & Pipelines → Create → ETL pipeline**, paste the file, set the configuration, **Run pipeline**.

# COMMAND ----------

print(dbutils.notebook.run(f"{src}/00_setup", 900, {
    "source_catalog": source_catalog, "source_schema": source_schema, "annuity_table": annuity_table,
    "life_table": life_table, "target_catalog": target_catalog, "target_schema": target_schema,
    "create_sample_data": dbutils.widgets.get("create_sample_data")}) or "setup done")

# COMMAND ----------

settings = dict(
    name=pipeline_name, catalog=target_catalog, schema=target_schema, serverless=True, development=True,
    libraries=[PipelineLibrary(file=FileLibrary(path=f"{root}/pipeline/policy_layers.sql"))],
    configuration={"source_catalog": source_catalog, "source_schema": source_schema,
                   "annuity_table": annuity_table, "life_table": life_table})
existing = [p for p in w.pipelines.list_pipelines(filter=f"name LIKE '{pipeline_name}'")]
if existing:
    pipeline_id = existing[0].pipeline_id
    w.pipelines.update(pipeline_id, **settings)
else:
    pipeline_id = w.pipelines.create(**settings).pipeline_id
print(f"Pipeline: {w.config.host}/pipelines/{pipeline_id}")

import time
update_id = w.pipelines.start_update(pipeline_id, full_refresh=True).update_id
while True:
    state = w.pipelines.get_update(pipeline_id, update_id).update.state.value
    if state in ("COMPLETED", "FAILED", "CANCELED"):
        break
    time.sleep(15)
print("Pipeline update:", state)
assert state == "COMPLETED", "Pipeline failed: open the pipeline link above and check the event log"

display(spark.sql(f"""
  SELECT 'policy_ruby' AS layer, count(*) AS rows, size(collect_set(product_line)) AS product_lines,
         (SELECT count(*) FROM information_schema.columns
          WHERE table_catalog = '{target_catalog}' AND table_schema = '{target_schema}' AND table_name = 'policy_ruby') AS columns
  FROM {tgt}.policy_ruby
  UNION ALL
  SELECT 'policy_diamond', count(*), size(collect_set(product_line)),
         (SELECT count(*) FROM information_schema.columns
          WHERE table_catalog = '{target_catalog}' AND table_schema = '{target_schema}' AND table_name = 'policy_diamond')
  FROM {tgt}.policy_diamond"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Module 2 · What happens after you've built a table you like
# MAGIC 1. **Data quality:** the pipeline records every expectation. Rows with no policy number were dropped in ruby.
# MAGIC 2. **Documentation and lineage:** every column has a comment; Catalog Explorer → **Lineage** shows source → ruby → diamond.
# MAGIC 3. **Certified metrics:** `src/01_metric_view` defines the business measures **once** in the metric view
# MAGIC    `policy_metrics` on the diamond table, and tags it as certified.

# COMMAND ----------

display(spark.sql(f"""
  SELECT origin.flow_name AS table_name, e.name AS expectation, e.passed_records, e.failed_records
  FROM event_log('{pipeline_id}')
  LATERAL VIEW explode(from_json(details:flow_progress:data_quality:expectations,
                       'array<struct<name:string,dataset:string,passed_records:bigint,failed_records:bigint>>')) x AS e
  WHERE event_type = 'flow_progress' AND details:flow_progress:data_quality IS NOT NULL
    AND origin.update_id = '{update_id}'
  ORDER BY table_name, expectation"""))

# COMMAND ----------

dbutils.notebook.run(f"{src}/01_metric_view", 600, {"target_catalog": target_catalog, "target_schema": target_schema})
display(spark.sql(f"""
  SELECT product_line, MEASURE(total_policies) AS total_policies, MEASURE(in_force_policies) AS in_force_policies,
         ROUND(100 * MEASURE(in_force_rate), 1) AS in_force_pct, ROUND(MEASURE(total_premium)) AS total_premium
  FROM {tgt}.policy_metrics GROUP BY ALL ORDER BY product_line"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Module 3 · AI/BI dashboard
# MAGIC Two datasets: the diamond table (for interactive visuals and filters) and the certified metric view (for the KPI
# MAGIC table). Visuals: 4 KPI counters, a monthly trend, three breakdowns, a certified-metrics table, and filters for product
# MAGIC line and status. Published **without embedded credentials**, so each viewer's own Unity Catalog permissions apply.

# COMMAND ----------

import base64
from databricks.sdk.service.workspace import ExportFormat
dash_path = f"{root}/dashboards/policy_overview.lvdash.json"
try:
    spec = json.load(open(dash_path))
except Exception:   # in Git folders .lvdash.json files are dashboard objects, so read them through the export API
    spec = json.loads(base64.b64decode(w.workspace.export(dash_path.removeprefix("/Workspace"),
                                                          format=ExportFormat.SOURCE).content))
for ds in spec["datasets"]:                       # unqualified names in the file resolve to the target schema
    ds["catalog"], ds["schema"] = target_catalog, target_schema
body = Dashboard(display_name=dashboard_name, warehouse_id=warehouse_id,
                 serialized_dashboard=json.dumps(spec), parent_path=os.path.dirname(nb_path))
existing = [d for d in w.lakeview.list() if d.display_name == dashboard_name]
if existing:
    dashboard_id = existing[0].dashboard_id
    w.lakeview.update(dashboard_id, dashboard=body)
else:
    dashboard_id = w.lakeview.create(dashboard=body).dashboard_id
w.lakeview.publish(dashboard_id, embed_credentials=False, warehouse_id=warehouse_id)
print(f"Dashboard: {w.config.host}/dashboardsv3/{dashboard_id}/published")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Module 4 · Genie Agent on the same data
# MAGIC Same diamond table and metric view as the dashboard, plus instructions, sample questions and example SQL, so a
# MAGIC business user's question returns the same numbers as the dashboard. Genie needs a **pro or serverless SQL
# MAGIC warehouse** and **partner-powered AI** turned on for the account and workspace.

# COMMAND ----------

gold = f"{target_catalog}.{target_schema}"
nid = iter(f"{i:032x}" for i in range(1, 100))   # Genie needs 32-hex ids, sorted within each list
space = {
    "version": 2,
    "config": {"sample_questions": [{"id": next(nid), "question": [q]} for q in [
        "How many policies are in force by product line?",
        "What is the in-force rate by product line and issue year?",
        "What is the total premium for annuities issued in the last 12 months?",
        "Which status has the highest average premium for life policies?"]]},
    "data_sources": {"tables": [
        {"identifier": f"{gold}.policy_diamond",
         "description": ["Diamond table: one row per annuity or life policy, with product line, standardised status, "
                         "issue date and premium. Built by the ruby → diamond pipeline."]},
        {"identifier": f"{gold}.policy_metrics",
         "description": ["Certified metric view: total_policies, in_force_policies, in_force_rate, total_premium, "
                         "avg_premium. Query measures with MEASURE()."]}]},
    "instructions": {
        "text_instructions": [{"id": next(nid), "content": [
            "You answer questions about annuity and life insurance policies.\n"
            "- Prefer the certified metric view policy_metrics for KPIs; use MEASURE(<measure>) and GROUP BY the dimensions asked for.\n"
            "- 'In force' or 'active' means policy_status = 'In force'. 'In-force rate' or 'persistency' is in_force_rate.\n"
            "- Premium means premium_amount: single premium for annuities, annualised planned premium for life. Say so when "
            "you add annuity and life premium together.\n"
            "- Product line is Annuity or Life.\n"
            "- Show rates as percentages with one decimal and amounts in USD with no decimals."]}],
        "example_question_sqls": [
            {"id": next(nid), "question": ["How many policies are in force by product line?"],
             "sql": [f"SELECT product_line, MEASURE(in_force_policies) AS in_force_policies, MEASURE(total_policies) AS total_policies "
                     f"FROM {gold}.policy_metrics GROUP BY ALL ORDER BY in_force_policies DESC"]},
            {"id": next(nid), "question": ["What is the in-force rate by product line and issue year?"],
             "sql": [f"SELECT product_line, issue_year, ROUND(100 * MEASURE(in_force_rate), 1) AS in_force_pct "
                     f"FROM {gold}.policy_metrics GROUP BY ALL ORDER BY product_line, issue_year"]}]},
}
gbody = {"title": genie_title, "warehouse_id": warehouse_id, "serialized_space": json.dumps(space),
         "description": "Ask about policy counts, in-force rate and premium by product line, status and issue period."}
found = [s for s in w.api_client.do("GET", "/api/2.0/genie/spaces").get("spaces", []) if s.get("title") == genie_title]
if found:
    space_id = found[0]["space_id"]
    w.api_client.do("PATCH", f"/api/2.0/genie/spaces/{space_id}", body=gbody)
else:
    space_id = w.api_client.do("POST", "/api/2.0/genie/spaces", body=gbody)["space_id"]
print(f"Genie Agent: {w.config.host}/genie/rooms/{space_id}")

msg = w.genie.start_conversation_and_wait(space_id, "How many policies are in force by product line?")
for att in msg.attachments or []:
    if att.query:
        print("Genie SQL:", att.query.query)
    if att.text:
        print("Genie says:", att.text.content)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Module 5 · Governance, sharing & access control
# MAGIC | Layer | Grant | Why |
# MAGIC |---|---|---|
# MAGIC | Data (Unity Catalog) | `USE CATALOG`, `USE SCHEMA`, and `SELECT` on **`policy_diamond` and `policy_metrics` only** | Viewers see the reporting layer; ruby and the sources stay private |
# MAGIC | Dashboard | `CAN RUN` | View and interact with the published dashboard (it queries as the viewer) |
# MAGIC | Genie Agent | `CAN RUN` | Ask questions (the warehouse uses the author's compute; data access is the viewer's) |

# COMMAND ----------

for stmt in [f"GRANT USE CATALOG ON CATALOG `{target_catalog}` TO `{group_name}`",
             f"GRANT USE SCHEMA ON SCHEMA {tgt} TO `{group_name}`",
             f"GRANT SELECT ON TABLE {tgt}.policy_diamond TO `{group_name}`",
             f"GRANT SELECT ON TABLE {tgt}.policy_metrics TO `{group_name}`"]:
    try:
        spark.sql(stmt)
        print("OK  ", stmt)
    except Exception as e:
        print("SKIP", stmt, "→", str(e).splitlines()[0][:160])
        print("     Unity Catalog grants need an ACCOUNT-level group (e.g. synced from Entra ID).")

for path, level in [(f"/api/2.0/permissions/dashboards/{dashboard_id}", "CAN_RUN"),
                    (f"/api/2.0/permissions/genie/{space_id}", "CAN_RUN"),
                    (f"/api/2.0/permissions/pipelines/{pipeline_id}", "CAN_VIEW")]:
    try:
        w.api_client.do("PATCH", path, body={"access_control_list": [{"group_name": group_name, "permission_level": level}]})
        print(f"OK   {level} for '{group_name}' on {path.split('/')[4]}")
    except Exception as e:
        print(f"SKIP {path}: {str(e)[:160]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Optional: schedule the pipeline
# MAGIC In the pipeline, **Schedule → Add schedule** (e.g. daily at 06:00). Ruby and diamond refresh incrementally where they
# MAGIC can, and the dashboard and Genie always read the latest diamond data. No changes to either.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Clean up
# MAGIC Set **Delete resources at the end** to `yes` and run this cell (deletes the pipeline, dashboard, Genie Agent and
# MAGIC target schema; source tables are untouched).

# COMMAND ----------

if dbutils.widgets.get("cleanup") == "yes":
    w.lakeview.trash(dashboard_id)
    w.api_client.do("DELETE", f"/api/2.0/genie/spaces/{space_id}")
    w.pipelines.delete(pipeline_id)
    spark.sql(f"DROP SCHEMA IF EXISTS {tgt} CASCADE")
    print("Deleted pipeline, dashboard, Genie Agent and target schema")
else:
    print("Kept resources (cleanup = no)")
