-- Module 2b · Certified metric view case_metrics — run in the SQL Editor
-- Replace <catalog>, <schema> (source) and <gold_schema> (target).
CREATE OR REPLACE VIEW <catalog>.<gold_schema>.case_metrics
WITH METRICS LANGUAGE YAML
COMMENT 'Certified case KPIs: volumes, open cases, days to close and SLA attainment by customer and case attributes.'
AS $$
version: 1.1
source: <catalog>.<gold_schema>.case_customer
fields:
  - name: opened_month
    expr: opened_month
    display_name: Opened Month
    synonyms: [month, period]
  - name: case_type
    expr: case_type
    display_name: Case Type
    synonyms: [type, category]
  - name: channel
    expr: channel
    display_name: Channel
  - name: priority
    expr: priority
    display_name: Priority
  - name: status
    expr: status
    display_name: Status
  - name: segment
    expr: segment
    display_name: Customer Segment
    synonyms: [segment, customer type]
  - name: region
    expr: region
    display_name: Region
  - name: is_vip
    expr: is_vip
    display_name: VIP Customer
measures:
  - name: total_cases
    expr: COUNT(1)
    display_name: Total Cases
    synonyms: [cases, case volume, number of cases]
  - name: open_cases
    expr: SUM(CASE WHEN is_open THEN 1 ELSE 0 END)
    display_name: Open Cases
    comment: Cases not yet closed (status open or pending).
    synonyms: [open, backlog, outstanding cases]
  - name: closed_cases
    expr: SUM(CASE WHEN is_open THEN 0 ELSE 1 END)
    display_name: Closed Cases
  - name: avg_days_to_close
    expr: AVG(days_to_close)
    display_name: Avg Days to Close
    comment: Average days from opened to closed, closed cases only.
    synonyms: [days to close, resolution time, time to close, average handling time]
  - name: sla_met_rate
    expr: AVG(CASE WHEN within_sla THEN 1.0 WHEN NOT within_sla THEN 0.0 END)
    display_name: SLA Met Rate
    comment: Share of closed cases closed within the SLA for their priority (high 2, medium 5, low 10 days).
    synonyms: [SLA, SLA attainment, on-time rate]
  - name: customers_with_cases
    expr: COUNT(DISTINCT customer_id)
    display_name: Customers with Cases
  - name: cases_per_customer
    expr: COUNT(1) / COUNT(DISTINCT customer_id)
    display_name: Cases per Customer
$$;

-- Optional: mark as certified (needs ASSIGN on the system.certification_status governed tag)
ALTER VIEW <catalog>.<gold_schema>.case_metrics SET TAGS ('system.certification_status' = 'certified');
