# Databricks notebook source
# MAGIC %md
# MAGIC # Module 1 · Layered architecture & the pipeline (30 min)
# MAGIC
# MAGIC **Goal:** turn two already-sourced tables into a reporting-ready table with a **Lakeflow pipeline**.
# MAGIC
# MAGIC | Layer | Table | What happens |
# MAGIC |---|---|---|
# MAGIC | Source | `annuity_policy`, `life_policy` | Already sourced. Left as they are |
# MAGIC | **Ruby** | `policy_ruby` | Both tables **unioned** into one conformed table: shared column names, `product_line`, standardised status. Rows with no policy number are dropped |
# MAGIC | **Diamond** | `policy_diamond` | Pared down to the **5 columns** reporting needs: `policy_number`, `product_line`, `policy_status`, `issue_date`, `premium_amount` |
# MAGIC
# MAGIC | Step | Time | What you do |
# MAGIC |---|---|---|
# MAGIC | 1 | 5 min | Look at the two sources |
# MAGIC | 2–4 | 10 min | Create the pipeline, paste the SQL, set the configuration |
# MAGIC | 5 | 10 min | Run it and explore the graph, row counts and expectations |
# MAGIC | 6 | 3 min | Check ruby and diamond |
# MAGIC | 7 | 2 min | Schedule it |
# MAGIC
# MAGIC **Prerequisite:** `00_Setup` has run. Attach to **Serverless** compute.

# COMMAND ----------

# MAGIC %pip install -q --upgrade "databricks-sdk>=0.60"

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %run ./_config

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1 · Look at the two sources (5 min)
# MAGIC Same business entity, but **different column names** (`policy_number` vs `policy_no`, `contract_status` vs
# MAGIC `policy_status`) and **different status spellings**. That's why the ruby layer maps columns before the union.

# COMMAND ----------

# MAGIC %sql
# MAGIC DESCRIBE TABLE IDENTIFIER(:source_catalog || '.' || :source_schema || '.' || :annuity_table);

# COMMAND ----------

# MAGIC %sql
# MAGIC DESCRIBE TABLE IDENTIFIER(:source_catalog || '.' || :source_schema || '.' || :life_table);

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Raw status values: the ruby layer standardises these
# MAGIC SELECT 'annuity' AS source, contract_status AS raw_status, count(*) AS rows
# MAGIC FROM IDENTIFIER(:source_catalog || '.' || :source_schema || '.' || :annuity_table) GROUP BY ALL
# MAGIC UNION ALL
# MAGIC SELECT 'life', policy_status, count(*)
# MAGIC FROM IDENTIFIER(:source_catalog || '.' || :source_schema || '.' || :life_table) GROUP BY ALL
# MAGIC ORDER BY source, raw_status;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2 · Create the pipeline (UI)
# MAGIC 1. In the left sidebar, open **Jobs & Pipelines → Create → ETL pipeline**.
# MAGIC 2. **Name:** `Policy layers (<your name>)`. The value for you is printed by the next cell.
# MAGIC 3. **Default catalog / schema:** your target catalog and schema (printed below).
# MAGIC 4. Make sure **Serverless** is on.
# MAGIC 5. Choose **Start with an empty file**, language **SQL**.

# COMMAND ----------

print(f"Pipeline name:   {pipeline_name}\nDefault catalog: {target_catalog}\nDefault schema:  {target_schema}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3 · Paste the pipeline SQL
# MAGIC In the **Lakeflow Pipelines Editor**, replace the file's contents with
# MAGIC [`pipeline/policy_layers.sql`](../pipeline/policy_layers.sql) from this Git folder (or **Add existing file** and pick it).
# MAGIC
# MAGIC Read through it together. Two definitions, nothing else:
# MAGIC - `policy_ruby`: two `SELECT`s, one per source, each mapping its columns to the shared names, joined by **`UNION ALL`**.
# MAGIC   Two **expectations**: `has_policy_number` (drop the row) and `known_status` (warn only).
# MAGIC - `policy_diamond`: `SELECT` of 5 columns `FROM policy_ruby`, plus an expectation that premium is positive.
# MAGIC
# MAGIC You never say "run ruby first". The pipeline reads the SQL and works out the order.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4 · Set the configuration
# MAGIC The SQL refers to the sources as `${source_catalog}.${source_schema}.${annuity_table}`. In the pipeline, open
# MAGIC **Settings → Configuration → Add configuration** and add these four keys (values printed below):

# COMMAND ----------

pipeline_config = {"source_catalog": source_catalog, "source_schema": source_schema,
                   "annuity_table": annuity_table, "life_table": life_table}
for k, v in pipeline_config.items():
    print(f"{k:15} = {v}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5 · Run the pipeline and explore it
# MAGIC Click **Run pipeline**. When it finishes (2–4 minutes), walk through:
# MAGIC 1. **The graph:** `annuity_policy` + `life_policy` → `policy_ruby` → `policy_diamond`.
# MAGIC 2. **Row counts** per table: ruby has fewer rows than the two sources together. Why?
# MAGIC 3. Click `policy_ruby` → **Data quality**: `has_policy_number` shows the dropped rows.
# MAGIC 4. **Change something:** remove a column from diamond, run again, and watch only what's needed recompute.
# MAGIC
# MAGIC ### Catch-up cell
# MAGIC Fell behind, or not allowed to create pipelines? Run the next cell. It creates (or updates) the same pipeline from
# MAGIC `pipeline/policy_layers.sql` and runs it.

# COMMAND ----------

from databricks.sdk.service.pipelines import PipelineLibrary, FileLibrary

settings = dict(
    name=pipeline_name, catalog=target_catalog, schema=target_schema, serverless=True, development=True,
    libraries=[PipelineLibrary(file=FileLibrary(path=f"{repo_root}/pipeline/policy_layers.sql"))],
    configuration=pipeline_config)
pipeline_id = find_pipeline_id()
if pipeline_id:
    w.pipelines.update(pipeline_id, **settings)
else:
    pipeline_id = w.pipelines.create(**settings).pipeline_id
print(f"Pipeline: {w.config.host}/pipelines/{pipeline_id}")

update_id = w.pipelines.start_update(pipeline_id, full_refresh=True).update_id
while (state := w.pipelines.get_update(pipeline_id, update_id).update.state.value) not in ("COMPLETED", "FAILED", "CANCELED"):
    time.sleep(15)
print("Pipeline run:", state)
assert state == "COMPLETED", "The run failed: open the pipeline link above and read the error in the event log"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6 · Check ruby and diamond
# MAGIC Ruby holds both product lines in one table; diamond has the same rows but only 5 columns.

# COMMAND ----------

layers = [("source: " + annuity_table, annuity), ("source: " + life_table, life),
          ("ruby: policy_ruby", ruby), ("diamond: policy_diamond", diamond)]
display(spark.createDataFrame(
    [(name, spark.table(t).count(), len(spark.table(t).columns)) for name, t in layers],
    "layer STRING, rows BIGINT, columns INT"))

# COMMAND ----------

display(spark.sql(f"SELECT * FROM {diamond} LIMIT 10"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 7 · Schedule it (2 min)
# MAGIC In the pipeline, click **Schedule → Add schedule** (for example, daily at 06:00). From now on the diamond table
# MAGIC refreshes by itself, and everything you build on it in the next modules (metric view, dashboard, Genie) always shows
# MAGIC the latest data, with no changes.
# MAGIC
# MAGIC ✅ **Module 1 done.** Next: `02_After_the_Table`.
