-- Module 2 · Certified metric view policy_metrics on the diamond table — run in the SQL Editor
-- Replace <target_catalog> and <target_schema> with the pipeline's catalog and schema.
CREATE OR REPLACE VIEW <target_catalog>.<target_schema>.policy_metrics
WITH METRICS LANGUAGE YAML
COMMENT 'Certified policy KPIs: policy counts, in-force rate and premium by product line, status and issue period.'
AS $$
version: 1.1
source: <target_catalog>.<target_schema>.policy_diamond
fields:
  - name: product_line
    expr: product_line
    display_name: Product Line
    synonyms: [line of business, LOB, product]
  - name: policy_status
    expr: policy_status
    display_name: Policy Status
    synonyms: [status]
  - name: issue_year
    expr: YEAR(issue_date)
    display_name: Issue Year
    synonyms: [year]
  - name: issue_month
    expr: DATE_TRUNC('MONTH', issue_date)
    display_name: Issue Month
    synonyms: [month, period]
measures:
  - name: total_policies
    expr: COUNT(1)
    display_name: Total Policies
    synonyms: [policies, policy count, number of policies, contracts]
  - name: in_force_policies
    expr: SUM(CASE WHEN policy_status = 'In force' THEN 1 ELSE 0 END)
    display_name: In-force Policies
    comment: Policies with status In force (active).
    synonyms: [in force, active policies, inforce]
  - name: in_force_rate
    expr: AVG(CASE WHEN policy_status = 'In force' THEN 1.0 ELSE 0.0 END)
    display_name: In-force Rate
    comment: Share of policies that are still in force.
    synonyms: [persistency, retention rate]
  - name: total_premium
    expr: SUM(premium_amount)
    display_name: Total Premium
    comment: Annuity single premium plus life annualised premium, USD.
    synonyms: [premium, written premium, sales]
  - name: avg_premium
    expr: AVG(premium_amount)
    display_name: Average Premium
    synonyms: [average premium, premium per policy]
$$;

-- Query it: every measure is wrapped in MEASURE()
SELECT product_line, MEASURE(total_policies), MEASURE(in_force_policies), MEASURE(in_force_rate), MEASURE(total_premium)
FROM <target_catalog>.<target_schema>.policy_metrics GROUP BY ALL;

-- Optional: mark as certified (needs ASSIGN on the system.certification_status governed tag)
ALTER VIEW <target_catalog>.<target_schema>.policy_metrics SET TAGS ('system.certification_status' = 'certified');
