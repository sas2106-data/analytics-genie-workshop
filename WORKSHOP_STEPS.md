# Two Tables → Gold View → Certified Metrics → Dashboard + Genie: step-by-step

**Audience:** report developers · **Duration:** 3.5 hours with 2 breaks · **Compute:** serverless SQL warehouse · **Architecture:** [`docs/architecture.png`](docs/architecture.png)

The flow:
- **① Source → modeled dataset:** profile two tables and join them.
- **② Gold view + certified metrics:** a documented view, plus a metric view.
- **③ AI/BI dashboard** for report developers.
- **④ Genie Agent** for business self-serve, on the same data.
- **⑤ DAB + Git check-in.**
- **⑥ Governance, sharing and access control.**

![Architecture](docs/architecture.png)

## What's in this repo

| Path | What it is |
|---|---|
| `sql/01_profile_and_join.sql` | Module 1, for the SQL Editor: profiling queries and the join |
| `sql/02_gold_view.sql`, `sql/03_metric_view.sql` | Module 2, for the SQL Editor: the gold view `case_customer` and the metric view `case_metrics` |
| `src/00_setup.py` … `02_metric_view.py` | The same steps as notebooks, run by the build job (`setup` can also create synthetic data) |
| `dashboards/case_overview.lvdash.json` | Module 3: the *Case Overview* AI/BI dashboard (answer key) |
| `databricks.yml` + `resources/*.yml` | Module 5: the bundle, containing the build job `analytics_build`, the dashboard `case_overview` and the Genie Agent `case_genie` |
| `notebooks/Workshop_Steps.py` | **Executable guide.** Runs modules 1, 2, 3, 4 and 6 in code. Use it for dry runs or as the answer key |

---

## Step 0 · Before the day (admins, about one week ahead)

**Account admin**
1. Attach the workspace to a Unity Catalog metastore.
2. Turn on **partner-powered AI features** at account and workspace level. Genie needs this.
3. Turn on **cross-Geo processing** if the workspace's Geo requires it for Genie.
4. Sync an Entra ID group for attendees and viewers into the **account**, e.g. `workshop-users`, and assign it to the workspace. Unity Catalog grants only accept account-level groups.

**Workspace admin**
5. Make sure there's a **serverless (or pro) SQL warehouse**, and give the group `CAN USE` on it.
6. **Entitlements:**
   - **Databricks SQL** for report developers (SQL Editor, dashboards, creating Genie Agents);
   - **consumer access** or Databricks SQL for viewers.
7. **Unity Catalog grants:**
   - `USE CATALOG` on the catalog;
   - `USE SCHEMA` and `SELECT` on the schema that holds `cases` and `customers`;
   - `CREATE SCHEMA` on the catalog, or pre-create a gold schema per attendee.
8. **Optional:** grant `ASSIGN` on the `system.certification_status` governed tag, so attendees can mark the metric view as certified.
9. Make this repo available in your Git provider. Attendees clone it as a **Git folder** and need Git credentials set under **Settings → Linked accounts**.
10. Decide how attendees run the Databricks CLI for Module 5: on a laptop, or in the workspace **web terminal**.

> **Not needed:** Databricks Apps, or any separate BI tool. AI/BI dashboards and Genie are built into the workspace.

**Source data**
- The workshop expects two tables that share `customer_id`:
  - `cases(case_id, customer_id, case_type, channel, priority, status, opened_date, closed_date)`
  - `customers(customer_id, customer_name, segment, region, customer_since, is_vip)`
- If your names differ, map them in `sql/02_gold_view.sql` (and `src/01_gold_view.py`).
- **No data yet?** Set `create_sample_data = true`. The setup step creates about 1,500 customers and about 8,000 cases, with messy status values and about 2% of cases whose customer is missing.

**Dry run (facilitator)**
1. Open `notebooks/Workshop_Steps` and set the widgets: `catalog`, `schema`, `warehouse_id` and `group_name`.
2. Click **Run all**. It takes about 10 minutes and ends with links to the dashboard and the Genie Agent.
3. Open both and check that they agree, for example on open cases by segment.
4. Set `cleanup = yes` and run the last cell.

---

## 0:00 · Welcome & objectives (5 min)

Introductions and goals for the day. Check that everyone can log in, open the **SQL Editor** and see the Git folder.

## 0:05 · Overview of Databricks (10 min)

| Platform area | What it does | Today |
|---|---|---|
| **Unity Catalog** | One governance layer: grants, row filters, column masks, lineage, audit, certified assets | Modules 2 and 6 |
| **Metric views** | Business measures defined once in Unity Catalog and reused by dashboards, Genie and SQL | Module 2 |
| **Databricks SQL** | Serverless SQL warehouses and the SQL Editor | Modules 1 and 2 |
| **AI/BI dashboards** | Governed, shareable dashboards built into the workspace | Module 3 |
| **Genie** | Natural-language questions over governed data (Genie Agents and Genie One) | Module 4 |
| **Asset Bundles & Git folders** | Infrastructure as code and CI/CD for the dashboard, Genie Agent and jobs | Module 5 |

End on the architecture diagram: one dataset, two surfaces.

## 0:15 · Module 1 — Source to modeled dataset (30 min)

1. Open the **SQL Editor**, choose the serverless warehouse, and paste in `sql/01_profile_and_join.sql`. Replace `<catalog>` and `<schema>`.
2. Run each query and discuss what it shows:
   - **Size and keys:** how many cases and customers there are, and how many distinct customer IDs appear in `cases`.
   - **Key uniqueness:** `customer_id` must be unique in `customers`, or the join multiplies rows.
   - **Orphans:** about 2% of cases have no matching customer. Decide between `INNER JOIN` (drops them) and `LEFT JOIN` (keeps them as `Unknown`). This workshop uses `LEFT JOIN`.
   - **Data quality:** `status` comes in six spellings (`open`, `Open `, `Pending`, `closed`, `Closed`, `CLOSED`). Standardise it in the gold view.
3. Run the join (query 5) and check the result.
4. In Catalog Explorer, check **Lineage** for `cases` (it fills in after Module 2).

## 0:45 · Module 2 — Gold view + certified metrics (35 min)

1. **Gold view:** run `sql/02_gold_view.sql`, replacing `<catalog>`, `<schema>` and `<gold_schema>`. It creates `case_customer`, with one row per case plus its customer. It standardises `status` and adds `is_open`, `days_to_close`, `sla_days` and `within_sla`, and every column has a comment.
2. In **Catalog Explorer**, open `case_customer`. Look at the column comments in the **Overview** tab, the **Lineage** tab (back to `cases` and `customers`), and **Sample data**.
3. **Certified metrics:** run `sql/03_metric_view.sql`. It creates the metric view `case_metrics`, which defines these measures once:

   | Measure | Definition |
   |---|---|
   | `total_cases` | `COUNT(1)` |
   | `open_cases` | not closed (open or pending) |
   | `avg_days_to_close` | closed cases only |
   | `sla_met_rate` | closed within 2, 5 or 10 days for high, medium or low priority |
   | `customers_with_cases` | distinct customers |
   | `cases_per_customer` | cases per distinct customer |

   It also defines the dimensions, with display names and synonyms that Genie uses.
4. Query it, wrapping every measure in `MEASURE()`:
   ```sql
   SELECT segment, MEASURE(total_cases), MEASURE(open_cases), MEASURE(avg_days_to_close), MEASURE(sla_met_rate)
   FROM <catalog>.<gold_schema>.case_metrics GROUP BY ALL;
   ```
5. **Certify it:** run the last line of the script, which tags the view `system.certification_status = certified`. This needs `ASSIGN` on the tag. Show the certified badge in Catalog Explorer.

> **Why a metric view?** If "SLA met" is computed in each chart or in each Genie answer, the numbers drift. Defining it once in Unity Catalog means the dashboard, Genie and ad-hoc SQL all agree.

## 1:20 · Break (15 min)

## 1:35 · Module 3 — Build the AI/BI dashboard (45 min)

1. Go to **Dashboards → Create dashboard** and open the **Data** tab. Add two datasets:
   - **Cases (gold view):** an SQL dataset that selects `case_id, opened_month, case_type, channel, priority, segment, region, is_open, days_to_close, within_sla` from `case_customer`. This dataset powers the interactive visuals and filters.
   - **Certified metrics:** choose **Add data → `case_metrics`** to use the metric view directly. Or use SQL with `MEASURE()` grouped by `segment, region`.
2. On the **Canvas**, build the visuals. `dashboards/case_overview.lvdash.json` is the answer key.

   | Visual | Field or measure |
   |---|---|
   | Counter: Total cases | `COUNT(case_id)` |
   | Counter: Open cases | `SUM(is_open)` |
   | Counter: Avg days to close | `AVG(days_to_close)` |
   | Counter: SLA met | `AVG(within_sla)`, formatted as a percentage |
   | Line: cases per month | `opened_month` × `COUNT(case_id)`, coloured by `case_type` |
   | Bar: open cases | by `case_type` |
   | Bar: avg days to close | by `channel` |
   | Bar: SLA met | by `priority` |
   | Table: certified metrics | the metric view, by `segment` and `region` |

3. Add **filters**: multi-select on `region`, `segment` and `case_type`. Connect `region` and `segment` to both datasets.
4. **Parameter exercise:** clone the *Cases* dataset, add `WHERE channel = :channel` (default `Web`), connect a single-select filter to the `channel` parameter, and point one bar chart at the clone.
5. **Publish:**
   - Turn **embed credentials** off, so viewers query with their own permissions.
   - **Share** with the group as **Can run**.
   - Copy the link.
6. **Check:** with no filters, the counters must match the certified table's totals. *Same numbers, one definition.*

## 2:20 · Module 4 — Create the Genie Agent (35 min)

1. Go to **Genie → New**, add `case_customer` and `case_metrics`, and choose the serverless warehouse.
2. Under **Instructions**, paste the text instructions from `resources/case_genie.yml`:
   - prefer the metric view, using `MEASURE()`;
   - define *open*, *SLA* and *days to close*;
   - explain the `Unknown` segment;
   - set formatting rules.
3. Add the two **example SQL** queries and the four **sample questions** from the same file.
4. Test business-style questions:
   - *How many cases are open by segment?* Compare with the dashboard: Retail is highest, and Genie should mention `Unknown`.
   - *What is the SLA met rate by priority?*
   - *Which channel takes longest to close?*, then follow up with *…and for VIP customers only?*
5. In **Monitor**, look at the questions asked and the SQL that was generated. Turn a good answer into a new example query.

## 2:55 · Break (10 min)

## 3:05 · Module 5 — Create the DAB and check it in (10 min)

**1 · Capture the UI-built objects as YAML**

Compare each generated file with `resources/*.yml`, then delete the generated ones.

```bash
databricks bundle generate dashboard   --existing-id <dashboard id>
databricks bundle generate genie-space --existing-id <space id>
```

**2 · Set the variables once per terminal**

This form works in bash and zsh.

```bash
export BUNDLE_VAR_catalog=<catalog>
export BUNDLE_VAR_schema=<source schema>
export BUNDLE_VAR_target_schema=<gold schema>_dab
export BUNDLE_VAR_warehouse_id=<warehouse id>
export BUNDLE_VAR_group_name=workshop-users
```

**3 · Deploy, build and check in**

```bash
databricks bundle validate -t dev
databricks bundle deploy   -t dev                 # creates the build job and the dashboard
databricks bundle run analytics_build -t dev      # builds the gold view and metric view
databricks bundle deploy   -t dev                 # now creates the Genie Agent (its tables exist)

git checkout -b feature/<you>-case-analytics
git add -A && git commit -m "Case dashboard and Genie Agent as a bundle"
git push -u origin HEAD                           # then open a pull request
```

What to point out:
- `dataset_catalog` and `dataset_schema` in `resources/case_dashboard.yml` point the dashboard's unqualified table names at each environment's gold schema. **The same dashboard file works in dev and prod.**
- Dev mode prefixes the dashboard and Genie names with `[dev <you>]`.
- **Promotion:** CI runs `bundle deploy -t prod` as a service principal after the pull request merges.

## 3:15 · Module 6 — Governance, sharing & access control (15 min)

| Layer | Grant | Where (bundle) |
|---|---|---|
| Data | `USE CATALOG` and `USE SCHEMA`, plus `SELECT` on the **gold** schema | Catalog Explorer → Permissions, or `GRANT …` |
| Dashboard | **Can run** (published) | Dashboard → Share (`resources/case_dashboard.yml`) |
| Genie Agent | **Can run** | Genie → Share (`resources/case_genie.yml`) |

```sql
GRANT USE CATALOG ON CATALOG <catalog> TO `workshop-users`;
GRANT USE SCHEMA, SELECT ON SCHEMA <catalog>.<gold_schema> TO `workshop-users`;
```

Discussion points:
- **The source tables stay private.** Viewers only need the gold schema, because the view reads the sources with its owner's rights.
- **Embedded credentials:** off means each viewer's Unity Catalog permissions apply. On means everyone sees what the publisher can see.
- **Genie:** compute runs on the author's embedded warehouse credentials, but **data access is always the end user's**.
- **Demo: different rows per viewer.** Row filters apply to tables, so filter the `cases` source table:
  ```sql
  CREATE FUNCTION <catalog>.<schema>.channel_filter(ch STRING) RETURN
    NOT is_account_group_member('workshop-users') OR ch IN ('Web', 'Phone');
  ALTER TABLE <catalog>.<schema>.cases SET ROW FILTER <catalog>.<schema>.channel_filter ON (channel);
  ```
  Group members now see only Web and Phone cases in both the dashboard and Genie. Remove the filter with `ALTER TABLE … DROP ROW FILTER;`.

Wrap up: one governed dataset, two surfaces, one set of numbers, deployed as code.

**Clean up:** run `databricks bundle destroy -t dev`, then run the notebook's last cell with `cleanup = yes`.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `MEASURE` errors such as *cannot resolve* | Every measure from a metric view must be wrapped in `MEASURE(<name>)`. Dimensions are not. |
| The join returns more rows than `cases` | `customer_id` isn't unique in `customers`. Run profiling query 2 and deduplicate first. |
| Dashboard viewers see *Permission denied* | Embed credentials is off, so grant the viewer `SELECT` on the gold schema, or turn embedding on. |
| `bundle deploy`: *Failed to fetch tables for the agent* | The gold view or metric view doesn't exist yet. Run `bundle run analytics_build`, then deploy again. |
| `bundle validate`: *no value assigned to required variable* | Export `BUNDLE_VAR_schema`, `BUNDLE_VAR_target_schema` and `BUNDLE_VAR_warehouse_id`. In zsh, `V="--var=…"; … $V` silently passes nothing. |
| The Genie sidebar icon shows but Genie won't open | Partner-powered AI features are off (account admin). |
| `GRANT … TO workshop-users` fails with *PRINCIPAL_DOES_NOT_EXIST* | The group is workspace-local. Use an account-level group. |
| `SET TAGS ('system.certification_status' …)` is denied | You need `ASSIGN` on that governed tag. Skip it, or ask an admin. |
