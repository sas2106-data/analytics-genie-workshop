-- Lakeflow Spark Declarative Pipeline: source → ruby → diamond
--
-- Paste this into a new ETL pipeline (Jobs & Pipelines → Create → ETL pipeline), or let the guided notebook create it.
-- Pipeline settings:
--   * Default catalog / schema = where ruby and diamond are written (your own schema)
--   * Configuration: source_catalog, source_schema, annuity_table, life_table
--
-- Using your own tables? Only the two SELECTs in policy_ruby change: map each source column to the ruby column name.

-- ── RUBY ── both sources in one conformed table: same column names, standardised status, one row per policy
CREATE OR REFRESH MATERIALIZED VIEW policy_ruby (
  policy_number        STRING        COMMENT 'Policy or contract number',
  customer_id          STRING        COMMENT 'Owner or insured (customer) key',
  product_line         STRING        COMMENT 'Annuity or Life',
  product_name         STRING        COMMENT 'Product or plan name',
  policy_status        STRING        COMMENT 'Standardised status: In force, Surrendered, Lapsed, Annuitized or Death claim',
  issue_date           DATE          COMMENT 'Issue date',
  issue_state          STRING        COMMENT 'US state of issue',
  premium_amount       DECIMAL(12,2) COMMENT 'Annuity: single premium at issue; Life: annualised planned premium (USD)',
  distribution_channel STRING        COMMENT 'Broker, Bank, Independent agent or Direct',
  source_table         STRING        COMMENT 'Source table the row came from',
  CONSTRAINT has_policy_number EXPECT (policy_number IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT known_status      EXPECT (policy_status <> 'Unknown')
)
COMMENT 'Ruby: annuity and life policies unioned into one conformed table.'
AS
SELECT policy_number,
       owner_id                                         AS customer_id,
       'Annuity'                                        AS product_line,
       product_name,
       CASE lower(trim(contract_status))
            WHEN 'active'      THEN 'In force'
            WHEN 'surrendered' THEN 'Surrendered'
            WHEN 'annuitized'  THEN 'Annuitized'
            WHEN 'death claim' THEN 'Death claim'
            ELSE 'Unknown' END                          AS policy_status,
       issue_date,
       issue_state,
       CAST(single_premium AS DECIMAL(12,2))            AS premium_amount,
       distribution_channel,
       '${annuity_table}'                               AS source_table
FROM ${source_catalog}.${source_schema}.${annuity_table}
UNION ALL
SELECT policy_no,
       insured_id,
       'Life',
       plan_name,
       CASE replace(lower(trim(policy_status)), ' ', '')
            WHEN 'inforce'     THEN 'In force'
            WHEN 'lapsed'      THEN 'Lapsed'
            WHEN 'surrendered' THEN 'Surrendered'
            WHEN 'deathclaim'  THEN 'Death claim'
            ELSE 'Unknown' END,
       issue_date,
       issue_state,
       CAST(annual_premium AS DECIMAL(12,2)),
       distribution_channel,
       '${life_table}'
FROM ${source_catalog}.${source_schema}.${life_table};

-- ── DIAMOND ── pared down to the 5 columns reporting needs
CREATE OR REFRESH MATERIALIZED VIEW policy_diamond (
  policy_number  STRING        COMMENT 'Policy or contract number',
  product_line   STRING        COMMENT 'Annuity or Life',
  policy_status  STRING        COMMENT 'In force, Surrendered, Lapsed, Annuitized or Death claim',
  issue_date     DATE          COMMENT 'Issue date',
  premium_amount DECIMAL(12,2) COMMENT 'Annuity: single premium; Life: annualised planned premium (USD)',
  CONSTRAINT positive_premium EXPECT (premium_amount > 0)
)
COMMENT 'Diamond: reporting-ready policy table (5 columns). Source for the certified metric view policy_metrics.'
AS
SELECT policy_number, product_line, policy_status, issue_date, premium_amount
FROM policy_ruby;
