# Databricks notebook source
# MAGIC %md
# MAGIC # Module 5 · Governance, sharing & access control (20 min)
# MAGIC
# MAGIC **Goal:** viewers get the **diamond layer only**. Ruby and the sources stay with the people who build the pipeline,
# MAGIC and one dashboard and one Genie Agent can show different rows to different people.
# MAGIC
# MAGIC | Step | Time | What you do |
# MAGIC |---|---|---|
# MAGIC | 1 | 5 min | Grant data access on diamond and the metric view only |
# MAGIC | 2 | 3 min | Share the dashboard, the Genie Agent and the pipeline |
# MAGIC | 3 | 4 min | Embedded credentials: whose permissions apply |
# MAGIC | 4 | 8 min | Demo: different rows per viewer with a row filter |
# MAGIC
# MAGIC **Prerequisite:** Modules 1–4 are done. Unity Catalog grants need an **account-level** group (e.g. synced from
# MAGIC Entra ID); set it in the **group** widget.

# COMMAND ----------

# MAGIC %pip install -q --upgrade "databricks-sdk>=0.60"

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %run ./_config

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1 · Grant data access: diamond and the metric view only
# MAGIC | Layer | Who sees it |
# MAGIC |---|---|
# MAGIC | Sources, `policy_ruby` | Pipeline builders only |
# MAGIC | `policy_diamond`, `policy_metrics` | Report developers and business users |
# MAGIC
# MAGIC In the UI: **Catalog → `policy_diamond` → Permissions → Grant → `SELECT`**, and the same on `policy_metrics`.
# MAGIC Or run:

# COMMAND ----------

for stmt in [f"GRANT USE CATALOG ON CATALOG `{target_catalog}` TO `{group_name}`",
             f"GRANT USE SCHEMA ON SCHEMA {tgt} TO `{group_name}`",
             f"GRANT SELECT ON TABLE {diamond} TO `{group_name}`",
             f"GRANT SELECT ON TABLE {metrics} TO `{group_name}`"]:
    try:
        spark.sql(stmt)
        print("OK  ", stmt)
    except Exception as e:
        print("SKIP", stmt, "→", str(e).splitlines()[0][:140])
        print("     Unity Catalog grants need an ACCOUNT-level group.")

# COMMAND ----------

# MAGIC %md
# MAGIC Check who can see what. The group appears on diamond and the metric view, **not** on ruby:

# COMMAND ----------

for t in (ruby, diamond, metrics):
    print(f"\n{t}")
    display(spark.sql(f"SHOW GRANTS ON TABLE {t}"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2 · Share the dashboard, the Genie Agent and the pipeline
# MAGIC | Object | Permission | Where |
# MAGIC |---|---|---|
# MAGIC | Dashboard | **Can run** | Dashboard → **Share** |
# MAGIC | Genie Agent | **Can run** | Genie Agent → **Share** |
# MAGIC | Pipeline (optional) | **Can view**: see runs and data quality, not edit | Pipeline → **Permissions** |
# MAGIC
# MAGIC Or run:

# COMMAND ----------

targets = [("dashboards", find_dashboard_id(), "CAN_RUN"), ("genie", find_genie_space_id(), "CAN_RUN"),
           ("pipelines", find_pipeline_id(), "CAN_VIEW")]
for kind, obj_id, level in targets:
    if not obj_id:
        print(f"SKIP {kind}: not found (run the earlier module first)")
        continue
    try:
        w.api_client.do("PATCH", f"/api/2.0/permissions/{kind}/{obj_id}",
                        body={"access_control_list": [{"group_name": group_name, "permission_level": level}]})
        print(f"OK   {level} for '{group_name}' on {kind}")
    except Exception as e:
        print(f"SKIP {kind}: {str(e)[:140]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3 · Embedded credentials: whose permissions apply
# MAGIC | Setting | Viewers query as… | Use when |
# MAGIC |---|---|---|
# MAGIC | Dashboard, **embed credentials off** (what you published) | **themselves**: their own grants and row filters apply | Data differs by viewer |
# MAGIC | Dashboard, embed credentials on | the publisher: everyone sees what the publisher sees | Same view for everyone, viewers have no table access |
# MAGIC | Genie Agent | compute runs on the author's warehouse; **data access is always the viewer's** | Always |
# MAGIC
# MAGIC That's why Step 1 matters: with embedding off, a viewer without `SELECT` on diamond gets *Permission denied*.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4 · Demo: one dashboard, different rows per viewer
# MAGIC Pipeline tables take their row filter **in their definition**. Three steps:
# MAGIC
# MAGIC **4a.** Run the next cell. It creates a filter function: members of the group see only **Life** policies; everyone
# MAGIC else sees everything.

# COMMAND ----------

filter_fn = f"{tgt}.product_filter"
spark.sql(f"""CREATE OR REPLACE FUNCTION {filter_fn}(pl STRING)
              RETURN NOT is_account_group_member('{group_name}') OR pl = 'Life'""")
print(f"Created {filter_fn}\n\nLine to add to policy_diamond in the pipeline (4b):\n"
      f"WITH ROW FILTER {target_catalog}.{target_schema}.product_filter ON (product_line)")

# COMMAND ----------

# MAGIC %md
# MAGIC **4b.** Open your pipeline in the **Lakeflow Pipelines Editor**. In `policy_diamond`, add the line printed above
# MAGIC between the closing `)` of the column list and `COMMENT 'Diamond: …'`:
# MAGIC ```sql
# MAGIC CREATE OR REFRESH MATERIALIZED VIEW policy_diamond (
# MAGIC   ...                                            -- columns and expectation as before
# MAGIC )
# MAGIC WITH ROW FILTER <target_catalog>.<target_schema>.product_filter ON (product_line)
# MAGIC COMMENT 'Diamond: ...'
# MAGIC AS SELECT ...
# MAGIC ```
# MAGIC Then click **Run pipeline**.
# MAGIC
# MAGIC **4c.** Run the next cell to confirm the filter is attached. Then have a group member open the **dashboard** and
# MAGIC **Genie**: they see only Life policies. Nothing in the dashboard or the Genie Agent changed.

# COMMAND ----------

info = spark.sql(f"DESCRIBE TABLE EXTENDED {diamond}").where("col_name = 'Row Filter'").collect()
print(f"Row filter on policy_diamond: {info[0].data_type}" if info else
      "No row filter yet: add the line in 4b and run the pipeline.")
display(spark.sql(f"SELECT product_line, count(*) AS rows_you_can_see FROM {diamond} GROUP BY ALL"))

# COMMAND ----------

# MAGIC %md
# MAGIC **Undo:** remove the `WITH ROW FILTER` line from the pipeline and run it again.
# MAGIC
# MAGIC ✅ **Workshop done:** two sources, two layers, one governed table, two surfaces, one set of numbers.
# MAGIC Run `06_Cleanup` when you're finished.
