# Genie Agent setup: Policies (Module 4)

Go to **Genie → New**, add `<target_catalog>.<target_schema>.policy_diamond` and
`<target_catalog>.<target_schema>.policy_metrics`, choose the serverless SQL warehouse, then paste in the items below.
The guided notebook creates the same agent.

## Title and description

- **Title:** Policies — Genie
- **Description:** Ask about policy counts, in-force rate and premium by product line (Annuity, Life), status and issue period.

## Table descriptions

| Table | Description |
|---|---|
| `policy_diamond` | Diamond table: one row per annuity or life policy, with product line, standardised status, issue date and premium. Built by the ruby → diamond pipeline. |
| `policy_metrics` | Certified metric view: total_policies, in_force_policies, in_force_rate, total_premium, avg_premium. Query measures with MEASURE(). |

## Text instructions

```
You answer questions about annuity and life insurance policies.
- Prefer the certified metric view policy_metrics for KPIs; use MEASURE(<measure>) and GROUP BY the dimensions asked for.
- "In force" or "active" means policy_status = 'In force'. "In-force rate" or "persistency" is in_force_rate.
- Premium means premium_amount: single premium for annuities, annualised planned premium for life. Say so when you
  add annuity and life premium together.
- Product line is Annuity or Life.
- Show rates as percentages with one decimal and amounts in USD with no decimals.
```

## Example SQL queries

**How many policies are in force by product line?**
```sql
SELECT product_line, MEASURE(in_force_policies) AS in_force_policies, MEASURE(total_policies) AS total_policies
FROM <target_catalog>.<target_schema>.policy_metrics GROUP BY ALL ORDER BY in_force_policies DESC
```

**What is the in-force rate by product line and issue year?**
```sql
SELECT product_line, issue_year, ROUND(100 * MEASURE(in_force_rate), 1) AS in_force_pct
FROM <target_catalog>.<target_schema>.policy_metrics GROUP BY ALL ORDER BY product_line, issue_year
```

## Sample questions

- How many policies are in force by product line?
- What is the in-force rate by product line and issue year?
- What is the total premium for annuities issued in the last 12 months?
- Which status has the highest average premium for life policies?
