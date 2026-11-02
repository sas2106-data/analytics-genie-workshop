# Genie Agent setup — Cases & Customers (Module 4)

Paste these into the Genie Agent (**Genie → New**, add `<catalog>.<gold_schema>.case_customer` and
`<catalog>.<gold_schema>.case_metrics`, choose the serverless SQL warehouse). The guided notebook creates the same agent.

## Title and description

- **Title:** Cases & Customers — Genie
- **Description:** Ask about case volumes, open cases, days to close and SLA by segment, region, case type and channel.

## Table descriptions

| Table | Description |
|---|---|
| `case_customer` | Gold view: one row per case joined to its customer (segment, region, VIP), with status, days_to_close and within_sla. |
| `case_metrics` | Certified metric view: total_cases, open_cases, avg_days_to_close, sla_met_rate, customers_with_cases. Query measures with MEASURE(). |

## Text instructions

```
You answer questions about customer service cases.
- Prefer the certified metric view case_metrics for KPIs; use MEASURE(<measure>) and GROUP BY the dimensions asked for.
- "Open" means not closed (status open or pending). "SLA" means sla_met_rate: closed within the target days for the priority (high 2, medium 5, low 10).
- "Days to close" is avg_days_to_close and only counts closed cases.
- Segment 'Unknown' means the case's customer is missing from the customer master; mention it if it appears.
- Show rates as percentages with one decimal and days with one decimal.
```

## Example SQL queries

**How many cases are open by segment?**
```sql
SELECT segment, MEASURE(open_cases) AS open_cases, MEASURE(total_cases) AS total_cases
FROM <catalog>.<gold_schema>.case_metrics GROUP BY ALL ORDER BY open_cases DESC
```

**What is the SLA met rate by priority?**
```sql
SELECT priority, ROUND(100 * MEASURE(sla_met_rate), 1) AS sla_met_pct, MEASURE(closed_cases) AS closed_cases
FROM <catalog>.<gold_schema>.case_metrics GROUP BY ALL ORDER BY sla_met_pct
```

## Sample questions

- How many cases are open by segment?
- What is the SLA met rate by priority?
- Which channel has the longest average days to close?
- Show monthly case volumes for Complaints over the last 6 months
