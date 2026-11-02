-- Module 2a · Gold view case_customer — run in the SQL Editor
-- Replace <catalog>, <schema> (source) and <gold_schema> (target).
CREATE OR REPLACE VIEW <catalog>.<gold_schema>.case_customer (
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
FROM <catalog>.<schema>.cases c
LEFT JOIN <catalog>.<schema>.customers cu ON c.customer_id = cu.customer_id;
