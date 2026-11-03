# Databricks notebook source
# MAGIC %md
# MAGIC # 00 · Setup
# MAGIC Checks that the two source tables (**annuity_policy** and **life_policy**) exist in `source_catalog.source_schema`,
# MAGIC and creates the target schema for the ruby and diamond tables. If `create_sample_data=true` and a source table is
# MAGIC missing, it creates synthetic data: ~3,000 annuity policies and ~5,000 life policies, with inconsistent status values
# MAGIC and a few rows without a policy number, so the pipeline's standardisation and expectations have something to do.

# COMMAND ----------

dbutils.widgets.text("source_catalog", "main")
dbutils.widgets.text("source_schema", "policy_src")
dbutils.widgets.text("annuity_table", "annuity_policy")
dbutils.widgets.text("life_table", "life_policy")
dbutils.widgets.text("target_catalog", "")            # blank = same as source_catalog
dbutils.widgets.text("target_schema", "policy_layers")
dbutils.widgets.dropdown("create_sample_data", "false", ["false", "true"])

src_catalog = dbutils.widgets.get("source_catalog")
src_schema = dbutils.widgets.get("source_schema")
tgt_catalog = dbutils.widgets.get("target_catalog").strip() or src_catalog
tgt_schema = dbutils.widgets.get("target_schema").strip()
annuity = f"`{src_catalog}`.`{src_schema}`.`{dbutils.widgets.get('annuity_table')}`"
life = f"`{src_catalog}`.`{src_schema}`.`{dbutils.widgets.get('life_table')}`"
sample = dbutils.widgets.get("create_sample_data") == "true"

spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{tgt_catalog}`.`{tgt_schema}`")

# COMMAND ----------

def ensure(table, select_sql, comment, column_comments):
    if spark.catalog.tableExists(table.replace("`", "")):
        return
    if not sample:
        raise ValueError(f"{table} not found. Pass the right catalog/schema/table names, or set create_sample_data=true.")
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{src_catalog}`.`{src_schema}`")
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

for t in (annuity, life):
    print(f"{t}: {spark.table(t.replace('`', '')).count()} rows")
