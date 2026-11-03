# Databricks notebook source
# MAGIC %md
# MAGIC # Workshop settings (shared)
# MAGIC Every module notebook starts with `%run ./_config`, so the settings below appear as widgets at the top of each
# MAGIC notebook. **Set them once per notebook** (or leave the defaults). Every resource gets your user name as a suffix, so
# MAGIC attendees don't collide.

# COMMAND ----------

dbutils.widgets.text("source_catalog", "main", "1 · Source catalog")
dbutils.widgets.text("source_schema", "policy_src", "2 · Source schema")
dbutils.widgets.text("annuity_table", "annuity_policy", "3 · Annuity table")
dbutils.widgets.text("life_table", "life_policy", "4 · Life table")
dbutils.widgets.text("target_catalog", "", "5 · Target catalog (blank = source catalog)")
dbutils.widgets.text("target_schema", "", "6 · Target schema (blank = policy_layers_<you>)")
dbutils.widgets.text("warehouse_id", "", "7 · SQL warehouse ID (blank = first serverless)")
dbutils.widgets.text("group_name", "workshop-users", "8 · Account-level group that gets access")

# COMMAND ----------

import json, os, re, time
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
me = w.current_user.me().user_name
suffix = re.sub(r"[^a-z0-9]", "-", me.split("@")[0].lower())[:16].strip("-")

source_catalog = dbutils.widgets.get("source_catalog").strip()
source_schema = dbutils.widgets.get("source_schema").strip()
annuity_table = dbutils.widgets.get("annuity_table").strip()
life_table = dbutils.widgets.get("life_table").strip()
target_catalog = dbutils.widgets.get("target_catalog").strip() or source_catalog
target_schema = dbutils.widgets.get("target_schema").strip() or f'policy_layers_{suffix.replace("-", "_")}'
group_name = dbutils.widgets.get("group_name").strip()
warehouse_id = dbutils.widgets.get("warehouse_id").strip() or next(
    (wh.id for wh in w.warehouses.list() if wh.enable_serverless_compute), None)

annuity = f"`{source_catalog}`.`{source_schema}`.`{annuity_table}`"
life = f"`{source_catalog}`.`{source_schema}`.`{life_table}`"
tgt = f"`{target_catalog}`.`{target_schema}`"
ruby, diamond, metrics = f"{tgt}.policy_ruby", f"{tgt}.policy_diamond", f"{tgt}.policy_metrics"

nb_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
repo_root = os.path.dirname(os.path.dirname(nb_path))
repo_root = repo_root if repo_root.startswith("/Workspace") else f"/Workspace{repo_root}"

pipeline_name = f"Policy layers ({suffix})"
dashboard_name = f"Policy Overview ({suffix})"
genie_title = f"Policies — Genie ({suffix})"

def find_pipeline_id():
    return next((p.pipeline_id for p in w.pipelines.list_pipelines(filter=f"name LIKE '{pipeline_name}'")), None)

def find_dashboard_id():
    return next((d.dashboard_id for d in w.lakeview.list() if d.display_name == dashboard_name), None)

def find_genie_space_id():
    spaces = w.api_client.do("GET", "/api/2.0/genie/spaces").get("spaces", [])
    return next((s["space_id"] for s in spaces if s.get("title") == genie_title), None)

print(f"you:       {me}\nsources:   {annuity}, {life}\ntarget:    {tgt}\nwarehouse: {warehouse_id}\n"
      f"pipeline:  {pipeline_name}\ndashboard: {dashboard_name}\ngenie:     {genie_title}")
