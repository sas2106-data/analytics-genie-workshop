# Databricks notebook source
# MAGIC %md
# MAGIC # 01 · Gold view `case_customer`
# MAGIC Joins cases to customers on `customer_id` (LEFT JOIN, so cases with a missing customer are kept as
# MAGIC `Unknown`), standardises status and adds `is_open`, `days_to_close` and `within_sla`. Every column has a
# MAGIC comment — Genie and the dashboard editor show them.

# COMMAND ----------

dbutils.widgets.text("catalog", "main")
dbutils.widgets.text("schema", "analytics_src")
dbutils.widgets.text("cases_table", "cases")
dbutils.widgets.text("customers_table", "customers")
dbutils.widgets.text("target_schema", "")

catalog = dbutils.widgets.get("catalog")
schema = dbutils.widgets.get("schema")
target = dbutils.widgets.get("target_schema").strip() or schema
cases = f"`{catalog}`.`{schema}`.`{dbutils.widgets.get('cases_table')}`"
customers = f"`{catalog}`.`{schema}`.`{dbutils.widgets.get('customers_table')}`"

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE VIEW `{catalog}`.`{target}`.case_customer (
  case_id        COMMENT 'Case key',
  customer_id    COMMENT 'Customer key',
  customer_name  COMMENT 'Customer name (Unknown if the customer is missing from the customer master)',
  segment        COMMENT 'Customer segment: Retail, SME, Corporate or Unknown',
  region         COMMENT 'Customer region: North, South, East, West, Central or Unknown',
  is_vip         COMMENT 'True for priority-service customers',
  case_type      COMMENT 'Claim, Complaint, Policy change, Billing or Cancellation',
  channel        COMMENT 'Web, Phone, Email or Broker',
  priority       COMMENT 'low, medium or high',
  status         COMMENT 'Standardised status: open, pending or closed',
  is_open        COMMENT 'True while the case is not closed (open or pending)',
  opened_date    COMMENT 'Date the case was opened',
  opened_month   COMMENT 'First day of the month the case was opened',
  closed_date    COMMENT 'Date the case was closed; NULL while open',
  days_to_close  COMMENT 'Days from opened to closed; NULL while open',
  sla_days       COMMENT 'Target days to close by priority: high 2, medium 5, low 10',
  within_sla     COMMENT 'True if closed within sla_days; NULL while open'
)
COMMENT 'Gold: one row per case, joined to its customer. Source for the certified metric view case_metrics.'
AS
SELECT c.case_id,
       c.customer_id,
       coalesce(cu.customer_name, 'Unknown'),
       coalesce(cu.segment, 'Unknown'),
       coalesce(cu.region, 'Unknown'),
       coalesce(cu.is_vip, false),
       c.case_type,
       c.channel,
       lower(trim(c.priority)),
       lower(trim(c.status)),
       lower(trim(c.status)) <> 'closed',
       c.opened_date,
       CAST(date_trunc('month', c.opened_date) AS DATE),
       c.closed_date,
       datediff(c.closed_date, c.opened_date),
       CASE lower(trim(c.priority)) WHEN 'high' THEN 2 WHEN 'medium' THEN 5 ELSE 10 END,
       CASE WHEN c.closed_date IS NOT NULL THEN datediff(c.closed_date, c.opened_date)
            <= CASE lower(trim(c.priority)) WHEN 'high' THEN 2 WHEN 'medium' THEN 5 ELSE 10 END END
FROM {cases} c
LEFT JOIN {customers} cu ON c.customer_id = cu.customer_id
""")
display(spark.sql(f"SELECT segment, count(*) AS cases FROM `{catalog}`.`{target}`.case_customer GROUP BY ALL ORDER BY cases DESC"))
