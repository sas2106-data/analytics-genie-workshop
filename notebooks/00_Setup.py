# Databricks notebook source
# MAGIC %md
# MAGIC # 00 · Setup (5 min, before Module 1)
# MAGIC
# MAGIC **Goal:** check that the two source tables exist, and create your own schema for the ruby and diamond tables.
# MAGIC
# MAGIC **Before you start:** attach this notebook to **Serverless** compute (top right).
# MAGIC
# MAGIC | Step | What you do |
# MAGIC |---|---|
# MAGIC | 1 | Set the widgets at the top: where the source tables are, and (optionally) your target catalog |
# MAGIC | 2 | Run the cells below, top to bottom |
# MAGIC | 3 | Note your **target schema**. You'll use it in every module |
# MAGIC
# MAGIC No source tables yet? Set **Synthetic data if missing** to `true`. It creates ~3,000 annuity and ~5,000 life policies
# MAGIC with inconsistent status values and a few rows without a policy number.

# COMMAND ----------

# MAGIC %run ./_config

# COMMAND ----------

dbutils.widgets.dropdown("create_sample_data", "false", ["false", "true"], "9 · Synthetic data if missing")
sample = dbutils.widgets.get("create_sample_data") == "true"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1 · Create your target schema
# MAGIC The pipeline in Module 1 writes `policy_ruby` and `policy_diamond` here. If you can't create schemas, ask the
# MAGIC facilitator for a pre-created one and type it into the **Target schema** widget.

# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {tgt} COMMENT 'Workshop: ruby and diamond policy tables'")
print(f"Target schema ready: {target_catalog}.{target_schema}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2 · Check the source tables (or create synthetic ones)

# COMMAND ----------

def ensure(table, select_sql, comment, column_comments):
    if spark.catalog.tableExists(table.replace("`", "")):
        print(f"Found {table}")
        return
    if not sample:
        raise ValueError(f"{table} not found. Fix the source widgets, or set 'Synthetic data if missing' to true.")
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{source_catalog}`.`{source_schema}`")
    spark.sql(f"CREATE TABLE {table} COMMENT '{comment}' AS {select_sql}")
    for col, text in column_comments.items():
        spark.sql(f"ALTER TABLE {table} ALTER COLUMN {col} COMMENT '{text}'")
    print(f"Created synthetic {table}")

STATES = "array('CA','TX','FL','NY','PA','IL','OH','MN','AZ','WA')"
CHANNELS = "array('Broker','Broker','Bank','Independent agent','Direct')"

ensure(annuity, f"""
  SELECT CASE WHEN id % 250 = 0 THEN NULL
              ELSE concat('ANN-', lpad(CAST(id AS STRING), 7, '0')) END                                AS policy_number,
         concat('C', lpad(CAST(CAST(rand(31) * 6000 AS INT) + 1 AS STRING), 6, '0'))                    AS owner_id,
         element_at(array('Fixed Index Annuity','Fixed Index Annuity','Fixed Annuity','Registered Index-Linked Annuity'),
                    CAST(rand(32) * 4 AS INT) + 1)                                                       AS product_name,
         element_at(array('Active','ACTIVE','active ','Active','Surrendered','Annuitized','Death Claim'),
                    CAST(rand(33) * 7 AS INT) + 1)                                                       AS contract_status,
         date_sub(current_date(), CAST(pow(rand(34), 0.8) * 3650 AS INT))                               AS issue_date,
         element_at({STATES}, CAST(rand(35) * 10 AS INT) + 1)                                            AS issue_state,
         CAST(round(10000 + pow(rand(36), 2) * 490000, -2) AS DECIMAL(12,2))                            AS single_premium,
         element_at({CHANNELS}, CAST(rand(37) * 5 AS INT) + 1)                                           AS distribution_channel
  FROM range(1, 3001)""",
  "Synthetic annuity contracts for the analytics workshop",
  {"policy_number": "Contract number, e.g. ANN-0000042; a few rows are missing it",
   "owner_id": "Contract owner (customer) key", "product_name": "Annuity product",
   "contract_status": "Raw contract status from the admin system (inconsistent casing)",
   "issue_date": "Contract issue date", "issue_state": "US state the contract was issued in",
   "single_premium": "Single premium paid at issue, USD", "distribution_channel": "How the contract was sold"})

ensure(life, f"""
  SELECT CASE WHEN id % 300 = 0 THEN NULL
              ELSE concat('LIF-', lpad(CAST(id AS STRING), 7, '0')) END                                AS policy_no,
         concat('C', lpad(CAST(CAST(rand(41) * 6000 AS INT) + 1 AS STRING), 6, '0'))                    AS insured_id,
         element_at(array('Term Life','Term Life','Indexed Universal Life','Universal Life','Whole Life'),
                    CAST(rand(42) * 5 AS INT) + 1)                                                       AS plan_name,
         element_at(array('In Force','in force','INFORCE','In Force','Lapsed','Surrendered','Death Claim'),
                    CAST(rand(43) * 7 AS INT) + 1)                                                       AS policy_status,
         date_sub(current_date(), CAST(pow(rand(44), 0.8) * 3650 AS INT))                               AS issue_date,
         element_at({STATES}, CAST(rand(45) * 10 AS INT) + 1)                                            AS issue_state,
         CAST(round(300 + pow(rand(46), 2) * 14700, 0) AS DECIMAL(12,2))                                AS annual_premium,
         element_at({CHANNELS}, CAST(rand(47) * 5 AS INT) + 1)                                           AS distribution_channel
  FROM range(1, 5001)""",
  "Synthetic life insurance policies for the analytics workshop",
  {"policy_no": "Policy number, e.g. LIF-0000042; a few rows are missing it",
   "insured_id": "Insured (customer) key", "plan_name": "Life insurance plan",
   "policy_status": "Raw policy status from the admin system (inconsistent spelling)",
   "issue_date": "Policy issue date", "issue_state": "US state the policy was issued in",
   "annual_premium": "Annualised planned premium, USD", "distribution_channel": "How the policy was sold"})

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3 · Confirm

# COMMAND ----------

display(spark.sql(f"""
  SELECT '{annuity_table}' AS source_table, count(*) AS rows FROM {annuity}
  UNION ALL SELECT '{life_table}', count(*) FROM {life}"""))
print(f"✅ Setup done. Your target schema is {target_catalog}.{target_schema}. Next: 01_Layered_Pipeline")
