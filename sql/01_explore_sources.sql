-- Module 1 · Quick look at the two sources (5 minutes) — run in the SQL Editor
-- Replace <source_catalog> and <source_schema>. The point: same business entity, different column names and status
-- values, so the ruby layer has to map them before the union.

-- 1. Column names side by side
DESCRIBE TABLE <source_catalog>.<source_schema>.annuity_policy;
DESCRIBE TABLE <source_catalog>.<source_schema>.life_policy;

-- 2. Row counts and missing policy numbers (the pipeline's expectation drops these)
SELECT 'annuity_policy' AS source, count(*) AS rows, count_if(policy_number IS NULL) AS missing_policy_number
FROM <source_catalog>.<source_schema>.annuity_policy
UNION ALL
SELECT 'life_policy', count(*), count_if(policy_no IS NULL)
FROM <source_catalog>.<source_schema>.life_policy;

-- 3. Raw status values (the ruby layer standardises them)
SELECT 'annuity_policy' AS source, contract_status AS raw_status, count(*) AS rows
FROM <source_catalog>.<source_schema>.annuity_policy GROUP BY ALL
UNION ALL
SELECT 'life_policy', policy_status, count(*)
FROM <source_catalog>.<source_schema>.life_policy GROUP BY ALL
ORDER BY source, raw_status;
