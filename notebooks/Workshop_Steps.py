# Databricks notebook source
# MAGIC %md
# MAGIC # Two Tables → Gold View → Certified Metrics → Dashboard + Genie — guided, executable steps
# MAGIC
# MAGIC Run top to bottom on **serverless** compute from the workshop Git folder. Each module does in code what the
# MAGIC facilitator shows in the UI (SQL Editor, dashboard editor, Genie), so attendees can catch up or re-run any step.
# MAGIC
# MAGIC | Module | What this notebook does |
# MAGIC |---|---|
# MAGIC | 1 · Source → modeled dataset | Profiles `cases` and `customers` (or creates synthetic ones) and validates the join on `customer_id` |
# MAGIC | 2 · Gold view + certified metrics | Creates the documented gold view `case_customer` and the metric view `case_metrics` |
# MAGIC | 3 · AI/BI dashboard | Creates and publishes the *Case Overview* dashboard from `dashboards/case_overview.lvdash.json` |
# MAGIC | 4 · Genie | Creates a Genie Agent (Genie space) on the gold view and metric view, and asks it a question |
# MAGIC | 5 · Governance & sharing | Unity Catalog grants, dashboard `CAN RUN`, Genie `CAN RUN` for a group |
# MAGIC
# MAGIC Every resource gets your user name as a suffix, so attendees don't collide.

# COMMAND ----------

# The Genie and Lakeview APIs need a recent Databricks SDK (older serverless images ship an older one)
%pip install -q --upgrade "databricks-sdk>=0.60"
dbutils.library.restartPython()

# COMMAND ----------

dbutils.widgets.text("catalog", "main", "1 · Catalog")
dbutils.widgets.text("schema", "analytics_src", "2 · Schema with cases + customers")
dbutils.widgets.text("cases_table", "cases", "3 · Cases table")
dbutils.widgets.text("customers_table", "customers", "4 · Customers table")
dbutils.widgets.text("target_schema", "", "5 · Gold schema (blank = <schema>_<you>)")
dbutils.widgets.dropdown("create_sample_data", "false", ["false", "true"], "6 · Synthetic data if missing")
dbutils.widgets.text("warehouse_id", "", "7 · SQL warehouse ID (blank = first serverless)")
dbutils.widgets.text("group_name", "workshop-users", "8 · Account-level group that gets access")
dbutils.widgets.dropdown("cleanup", "no", ["no", "yes"], "9 · Delete resources at the end")

# COMMAND ----------

import json, os, re
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.dashboards import Dashboard

w = WorkspaceClient()
me = w.current_user.me().user_name
suffix = re.sub(r"[^a-z0-9]", "-", me.split("@")[0].lower())[:16].strip("-")

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
cases_table = dbutils.widgets.get("cases_table")
customers_table = dbutils.widgets.get("customers_table")
target_schema = dbutils.widgets.get("target_schema").strip() or f'{schema}_{suffix.replace("-", "_")}'
create_sample_data = dbutils.widgets.get("create_sample_data")
warehouse_id = dbutils.widgets.get("warehouse_id").strip() or next(
    (wh.id for wh in w.warehouses.list() if wh.enable_serverless_compute), None)
group_name = dbutils.widgets.get("group_name").strip()

nb_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
root = os.path.dirname(os.path.dirname(nb_path))
root = root if root.startswith("/Workspace") else f"/Workspace{root}"
src = f"{root}/src"
gold = f"{catalog}.{target_schema}"
args = {"catalog": catalog, "schema": schema, "cases_table": cases_table, "customers_table": customers_table,
        "target_schema": target_schema, "create_sample_data": create_sample_data}

dashboard_name = f"Case Overview ({suffix})"
genie_title = f"Cases & Customers — Genie ({suffix})"
print(f"user={me}\nsource={catalog}.{schema}.{{{cases_table},{customers_table}}}\ngold={gold}\n"
      f"warehouse={warehouse_id}\nrepo root={root}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Module 1 · Source to modeled dataset
# MAGIC In the SQL Editor attendees run `sql/01_profile_and_join.sql`. Here: create the source tables if asked
# MAGIC (`src/00_setup`), then profile them — row counts, key uniqueness, orphan cases and raw status values.

# COMMAND ----------

print(dbutils.notebook.run(f"{src}/00_setup", 900, args) or "setup done")
c, cu = f"`{catalog}`.`{schema}`.`{cases_table}`", f"`{catalog}`.`{schema}`.`{customers_table}`"
display(spark.sql(f"""
  SELECT (SELECT count(*) FROM {c})                                         AS cases,
         (SELECT count(*) FROM {cu})                                        AS customers,
         (SELECT count(*) - count(DISTINCT customer_id) FROM {cu})          AS duplicate_customer_ids,
         (SELECT count(*) FROM {c} x LEFT ANTI JOIN {cu} y USING (customer_id)) AS orphan_cases"""))
display(spark.sql(f"SELECT status, count(*) AS cases FROM {c} GROUP BY status ORDER BY status"))

# COMMAND ----------

# MAGIC %md
# MAGIC **What the profile tells us:** `customer_id` is unique in customers (safe to join), ~2% of cases have no
# MAGIC customer (so **LEFT JOIN** and label them `Unknown`, rather than silently dropping them with an INNER JOIN), and
# MAGIC `status` needs standardising.
# MAGIC
# MAGIC ## Module 2 · Gold view + certified metrics
# MAGIC `src/01_gold_view` creates the documented view `case_customer` (every column has a comment);
# MAGIC `src/02_metric_view` defines the business measures **once** in the metric view `case_metrics`.

# COMMAND ----------

dbutils.notebook.run(f"{src}/01_gold_view", 600, args)
dbutils.notebook.run(f"{src}/02_metric_view", 600, args)
display(spark.sql(f"""
  SELECT segment, MEASURE(total_cases) AS total_cases, MEASURE(open_cases) AS open_cases,
         ROUND(MEASURE(avg_days_to_close), 1) AS avg_days_to_close, ROUND(100 * MEASURE(sla_met_rate), 1) AS sla_met_pct
  FROM {gold}.case_metrics GROUP BY ALL ORDER BY total_cases DESC"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Module 3 · AI/BI dashboard
# MAGIC The dashboard has two datasets: the gold view (for interactive visuals and filters) and the certified metric
# MAGIC view (for the KPI table). Visuals: 4 KPI counters, a monthly trend, two breakdowns, a certified-metrics table, and
# MAGIC filters for region, segment and case type. Published **without embedded credentials**, so each viewer's own
# MAGIC Unity Catalog permissions apply.

# COMMAND ----------

import base64
from databricks.sdk.service.workspace import ExportFormat
dash_path = f"{root}/dashboards/case_overview.lvdash.json"
try:
    spec = json.load(open(dash_path))
except Exception:   # in Git folders .lvdash.json files are dashboard objects, so read them through the export API
    spec = json.loads(base64.b64decode(w.workspace.export(dash_path.removeprefix("/Workspace"),
                                                          format=ExportFormat.SOURCE).content))
for ds in spec["datasets"]:                       # unqualified names in the file resolve to the gold schema
    ds["catalog"], ds["schema"] = catalog, target_schema
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
# MAGIC Same gold view and metric view as the dashboard, plus instructions, sample questions and example SQL — so a
# MAGIC business user's question returns the same numbers as the dashboard. Genie needs a **pro or serverless SQL
# MAGIC warehouse** and **partner-powered AI** turned on for the account and workspace.

# COMMAND ----------

nid = iter(f"{i:032x}" for i in range(1, 100))   # Genie needs 32-hex ids, sorted within each list
space = {
    "version": 2,
    "config": {"sample_questions": [{"id": next(nid), "question": [q]} for q in [
        "How many cases are open by segment?", "What is the SLA met rate by priority?",
        "Which channel has the longest average days to close?",
        "Show monthly case volumes for Complaints over the last 6 months"]]},
    "data_sources": {"tables": [
        {"identifier": f"{gold}.case_customer",
         "description": ["Gold view: one row per case joined to its customer (segment, region, VIP), with status, "
                         "days_to_close and within_sla."]},
        {"identifier": f"{gold}.case_metrics",
         "description": ["Certified metric view: total_cases, open_cases, avg_days_to_close, sla_met_rate, "
                         "customers_with_cases. Query measures with MEASURE()."]}]},
    "instructions": {
        "text_instructions": [{"id": next(nid), "content": [
            "You answer questions about customer service cases.\n"
            "- Prefer the certified metric view case_metrics for KPIs; use MEASURE(<measure>) and GROUP BY the dimensions asked for.\n"
            "- 'Open' means not closed (status open or pending). 'SLA' means sla_met_rate: closed within the target days "
            "for the priority (high 2, medium 5, low 10).\n"
            "- 'Days to close' is avg_days_to_close and only counts closed cases.\n"
            "- Segment 'Unknown' means the case's customer is missing from the customer master; mention it if it appears.\n"
            "- Show rates as percentages with one decimal and days with one decimal."]}],
        "example_question_sqls": [
            {"id": next(nid), "question": ["How many cases are open by segment?"],
             "sql": [f"SELECT segment, MEASURE(open_cases) AS open_cases, MEASURE(total_cases) AS total_cases "
                     f"FROM {gold}.case_metrics GROUP BY ALL ORDER BY open_cases DESC"]},
            {"id": next(nid), "question": ["What is the SLA met rate by priority?"],
             "sql": [f"SELECT priority, ROUND(100 * MEASURE(sla_met_rate), 1) AS sla_met_pct, MEASURE(closed_cases) AS closed_cases "
                     f"FROM {gold}.case_metrics GROUP BY ALL ORDER BY sla_met_pct"]}]},
}
gbody = {"title": genie_title, "warehouse_id": warehouse_id, "serialized_space": json.dumps(space),
         "description": "Ask about case volumes, open cases, days to close and SLA by segment, region, case type and channel."}
found = [s for s in w.api_client.do("GET", "/api/2.0/genie/spaces").get("spaces", []) if s.get("title") == genie_title]
if found:
    space_id = found[0]["space_id"]
    w.api_client.do("PATCH", f"/api/2.0/genie/spaces/{space_id}", body=gbody)
else:
    space_id = w.api_client.do("POST", "/api/2.0/genie/spaces", body=gbody)["space_id"]
print(f"Genie Agent: {w.config.host}/genie/rooms/{space_id}")

msg = w.genie.start_conversation_and_wait(space_id, "How many cases are open by segment?")
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
# MAGIC | Data (Unity Catalog) | `USE CATALOG`, `USE SCHEMA`, `SELECT` on the gold schema | The dashboard (no embedded credentials) and Genie both query as the viewer |
# MAGIC | Dashboard | `CAN RUN` | View and interact with the published dashboard |
# MAGIC | Genie Agent | `CAN RUN` | Ask questions (the warehouse uses the author's embedded compute credentials) |
# MAGIC
# MAGIC Source tables stay private: viewers only need the gold schema, because the view's owner reads the sources.

# COMMAND ----------

for stmt in [f"GRANT USE CATALOG ON CATALOG `{catalog}` TO `{group_name}`",
             f"GRANT USE SCHEMA, SELECT ON SCHEMA `{catalog}`.`{target_schema}` TO `{group_name}`"]:
    try:
        spark.sql(stmt)
        print("OK  ", stmt)
    except Exception as e:
        print("SKIP", stmt, "→", str(e).splitlines()[0][:160])
        print("     Unity Catalog grants need an ACCOUNT-level group (e.g. synced from Entra ID).")

for path, level in [(f"/api/2.0/permissions/dashboards/{dashboard_id}", "CAN_RUN"),
                    (f"/api/2.0/permissions/genie/{space_id}", "CAN_RUN")]:
    try:
        w.api_client.do("PATCH", path, body={"access_control_list": [{"group_name": group_name, "permission_level": level}]})
        print(f"OK   {level} for '{group_name}' on {path.split('/')[4]}")
    except Exception as e:
        print(f"SKIP {path}: {str(e)[:160]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Optional: one dashboard, different rows per viewer
# MAGIC Because the dashboard runs with each viewer's credentials, a row filter on the gold data changes what each person
# MAGIC sees — no dashboard changes. Row filters apply to tables, so filter the `cases` source table that feeds the
# MAGIC view (members of `<group>` see only Web and Phone cases; everyone else sees everything):
# MAGIC ```sql
# MAGIC CREATE FUNCTION <catalog>.<schema>.channel_filter(ch STRING) RETURN
# MAGIC   NOT is_account_group_member('<group>') OR ch IN ('Web', 'Phone');
# MAGIC ALTER TABLE <catalog>.<schema>.cases SET ROW FILTER <catalog>.<schema>.channel_filter ON (channel);
# MAGIC -- undo: ALTER TABLE <catalog>.<schema>.cases DROP ROW FILTER;
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## Clean up
# MAGIC Set **Delete resources at the end** to `yes` and run this cell (drops only the gold schema; sources untouched).

# COMMAND ----------

if dbutils.widgets.get("cleanup") == "yes":
    w.lakeview.trash(dashboard_id)
    w.api_client.do("DELETE", f"/api/2.0/genie/spaces/{space_id}")
    spark.sql(f"DROP SCHEMA IF EXISTS `{catalog}`.`{target_schema}` CASCADE")
    print("Deleted dashboard, Genie Agent and gold schema")
else:
    print("Kept resources (cleanup = no)")
