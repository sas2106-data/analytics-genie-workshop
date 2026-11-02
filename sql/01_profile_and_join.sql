-- Module 1 · Source to modeled dataset — run in the SQL Editor
-- Replace <catalog> and <schema> with the catalog/schema that hold the two source tables.
USE CATALOG <catalog>;
USE SCHEMA <schema>;

-- 1. Size and keys
SELECT 'cases' AS tbl, count(*) AS rows, count(DISTINCT customer_id) AS distinct_customer_ids FROM cases
UNION ALL
SELECT 'customers', count(*), count(DISTINCT customer_id) FROM customers;

-- 2. Is customer_id unique in customers? (should return no rows)
SELECT customer_id, count(*) AS n FROM customers GROUP BY customer_id HAVING count(*) > 1;

-- 3. Cases whose customer is missing from the customer master (decides INNER vs LEFT JOIN)
SELECT count(*) AS orphan_cases
FROM cases c LEFT ANTI JOIN customers cu ON c.customer_id = cu.customer_id;

-- 4. Data quality: raw status values (inconsistent casing / spaces → standardise in the gold view)
SELECT status, count(*) AS cases FROM cases GROUP BY status ORDER BY status;

-- 5. The join — LEFT JOIN keeps orphan cases as 'Unknown'
SELECT c.case_id, c.customer_id,
       coalesce(cu.segment, 'Unknown') AS segment,
       coalesce(cu.region,  'Unknown') AS region,
       c.case_type, c.channel, lower(trim(c.status)) AS status,
       c.opened_date, c.closed_date,
       datediff(c.closed_date, c.opened_date) AS days_to_close
FROM cases c
LEFT JOIN customers cu ON c.customer_id = cu.customer_id
LIMIT 100;
