# Databricks notebook source
# MAGIC %md
# MAGIC # Run all modules (facilitator dry run)
# MAGIC Runs `00_Setup` → `05_Governance` in order with the settings below, using each notebook's catch-up cells.
# MAGIC Takes about 10 minutes and prints the links to the pipeline, dashboard and Genie Agent.
# MAGIC Attendees don't need this: they work through the module notebooks one by one.

# COMMAND ----------

# MAGIC %run ./_config

# COMMAND ----------

dbutils.widgets.dropdown("create_sample_data", "false", ["false", "true"], "9 · Synthetic data if missing")
args = {k: dbutils.widgets.get(k) for k in
        ["source_catalog", "source_schema", "annuity_table", "life_table", "target_catalog", "target_schema",
         "warehouse_id", "group_name", "create_sample_data"]}
args["target_schema"] = target_schema   # pin the resolved name so every module uses the same schema

for nb in ["00_Setup", "01_Layered_Pipeline", "02_After_the_Table", "03_AIBI_Dashboard", "04_Genie_Agent", "05_Governance"]:
    t0 = time.time()
    dbutils.notebook.run(f"./{nb}", 1800, args)
    print(f"✅ {nb} ({time.time() - t0:.0f}s)")

print(f"\nPipeline:  {w.config.host}/pipelines/{find_pipeline_id()}\n"
      f"Dashboard: {w.config.host}/dashboardsv3/{find_dashboard_id()}/published\n"
      f"Genie:     {w.config.host}/genie/rooms/{find_genie_space_id()}")
