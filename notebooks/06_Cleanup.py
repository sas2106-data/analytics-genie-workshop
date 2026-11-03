# Databricks notebook source
# MAGIC %md
# MAGIC # 06 · Clean up
# MAGIC Deletes **your** workshop resources: the pipeline, dashboard and Genie Agent named with your suffix, and your target
# MAGIC schema (ruby, diamond, metric view, filter function). The **source tables are not touched**.
# MAGIC
# MAGIC Set **Confirm delete** to `yes`, then run all cells.

# COMMAND ----------

# MAGIC %pip install -q --upgrade "databricks-sdk>=0.60"

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %run ./_config

# COMMAND ----------

dbutils.widgets.dropdown("confirm_delete", "no", ["no", "yes"], "9 · Confirm delete")
assert target_schema != source_schema or target_catalog != source_catalog, \
    "Target schema is the source schema: refusing to drop it."
print(f"Will delete: pipeline '{pipeline_name}', dashboard '{dashboard_name}', Genie '{genie_title}', schema {tgt}")

# COMMAND ----------

if dbutils.widgets.get("confirm_delete") != "yes":
    print("Nothing deleted: set 'Confirm delete' to yes and run again.")
else:
    if (d := find_dashboard_id()):
        w.lakeview.trash(d); print("Deleted dashboard")
    if (s := find_genie_space_id()):
        w.api_client.do("DELETE", f"/api/2.0/genie/spaces/{s}"); print("Deleted Genie Agent")
    if (p := find_pipeline_id()):
        w.pipelines.delete(p); print("Deleted pipeline")
    spark.sql(f"DROP SCHEMA IF EXISTS {tgt} CASCADE"); print(f"Dropped schema {tgt}")
