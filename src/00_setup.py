# Databricks notebook source
# MAGIC %md
# MAGIC # 00 · Setup
# MAGIC Checks the two source tables (**cases** and **customers**) in the `schema` passed to the job and creates the
# MAGIC target (gold) schema. If `create_sample_data=true` and a source table is missing, creates synthetic data:
# MAGIC ~1,500 customers and ~8,000 cases, with messy status values and ~2% of cases whose customer is missing
# MAGIC (so profiling and the LEFT JOIN have something to find).

# COMMAND ----------

dbutils.widgets.text("catalog", "main")
dbutils.widgets.text("schema", "analytics_src")      # schema with the two source tables (job parameter)
dbutils.widgets.text("cases_table", "cases")
dbutils.widgets.text("customers_table", "customers")
dbutils.widgets.text("target_schema", "")             # blank = same as schema
dbutils.widgets.dropdown("create_sample_data", "false", ["false", "true"])

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
target = dbutils.widgets.get("target_schema").strip() or schema
cases = f"`{catalog}`.`{schema}`.`{dbutils.widgets.get('cases_table')}`"
customers = f"`{catalog}`.`{schema}`.`{dbutils.widgets.get('customers_table')}`"
sample = dbutils.widgets.get("create_sample_data") == "true"

spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{catalog}`.`{target}`")

# COMMAND ----------

def ensure(table, select_sql, comment, column_comments):
    if spark.catalog.tableExists(table.replace("`", "")):
        return
    if not sample:
        raise ValueError(f"{table} not found. Pass the right schema/table names, or set create_sample_data=true.")
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{catalog}`.`{schema}`")
    spark.sql(f"CREATE TABLE {table} COMMENT '{comment}' AS {select_sql}")
    for col, text in column_comments.items():
        spark.sql(f"ALTER TABLE {table} ALTER COLUMN {col} COMMENT '{text}'")
    print(f"Created synthetic {table}")

ensure(customers, """
  SELECT concat('CUST-', lpad(CAST(id AS STRING), 5, '0'))                                              AS customer_id,
         concat('Customer ', CAST(id AS STRING))                                                         AS customer_name,
         element_at(array('Retail','Retail','Retail','SME','SME','Corporate'), CAST(rand(11) * 6 AS INT) + 1) AS segment,
         element_at(array('North','South','East','West','Central'), CAST(rand(12) * 5 AS INT) + 1)        AS region,
         date_sub(current_date(), CAST(rand(13) * 3650 AS INT))                                           AS customer_since,
         rand(14) < 0.08                                                                                  AS is_vip
  FROM range(1, 1501)""",
  "Synthetic customer master for the analytics workshop",
  {"customer_id": "Customer key, e.g. CUST-00042", "customer_name": "Synthetic customer name",
   "segment": "Retail, SME or Corporate", "region": "Sales region: North, South, East, West or Central",
   "customer_since": "Date the customer relationship started", "is_vip": "True for priority-service customers"})

ensure(cases, """
  WITH base AS (
    SELECT id,
           date_sub(current_date(), CAST(pow(rand(21), 1.3) * 365 AS INT))           AS opened_date,
           element_at(array('low','medium','medium','high'), CAST(rand(22) * 4 AS INT) + 1) AS priority,
           CAST(exp(rand(23) * 3.2) AS INT)                                           AS lag_days,
           rand(24)                                                                   AS r
    FROM range(1, 8001)),
  shaped AS (
    SELECT *, date_add(opened_date, lag_days) > current_date() OR r < 0.06 AS still_open FROM base)
  SELECT concat('CASE-', lpad(CAST(id AS STRING), 6, '0'))                                     AS case_id,
         -- ids above 1500 have no customer: profiling finds them, the LEFT JOIN keeps them as Unknown
         concat('CUST-', lpad(CAST(CAST(rand(25) * 1530 AS INT) + 1 AS STRING), 5, '0'))     AS customer_id,
         element_at(array('Claim','Claim','Complaint','Policy change','Billing','Cancellation'), CAST(rand(26) * 6 AS INT) + 1) AS case_type,
         element_at(array('Web','Phone','Email','Broker'), CAST(rand(27) * 4 AS INT) + 1)    AS channel,
         priority,
         CASE WHEN still_open THEN element_at(array('open','Open ','Pending'), CAST(rand(28) * 3 AS INT) + 1)
              ELSE element_at(array('closed','Closed','CLOSED'), CAST(rand(29) * 3 AS INT) + 1) END AS status,
         opened_date,
         CASE WHEN still_open THEN NULL ELSE date_add(opened_date, lag_days) END             AS closed_date
  FROM shaped""",
  "Synthetic service cases for the analytics workshop",
  {"case_id": "Case key, e.g. CASE-000123", "customer_id": "Customer key; joins to customers.customer_id",
   "case_type": "Claim, Complaint, Policy change, Billing or Cancellation",
   "channel": "Channel the case came in on: Web, Phone, Email or Broker", "priority": "low, medium or high",
   "status": "Raw case status from the source system (inconsistent casing)",
   "opened_date": "Date the case was opened", "closed_date": "Date the case was closed; NULL while open"})

for t in (cases, customers):
    print(f"{t}: {spark.table(t.replace('`', '')).count()} rows")
