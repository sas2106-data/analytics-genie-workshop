# Two Tables → Ruby → Diamond → Certified Metrics → Dashboard + Genie: hands-on workshop

A 3.5-hour, hands-on workshop for **report developers**. You start with two related tables that are already sourced, build
a **layered pipeline** that turns them into a reporting-ready table, and then spend most of the day on what happens
**after** you have a table you like: certify and document it, report on it, open it up to plain-language questions, and
control who sees what.

The steps:
- **① Layered architecture & pipeline:** a Lakeflow pipeline **unions** `annuity_policy` and `life_policy` into the
  **ruby** table, then pares it down to **5 columns** in the **diamond** table.
- **② After the table:** data-quality results, lineage, column docs, and a certified Unity Catalog **metric view**.
- **③ AI/BI dashboard** with filters and a shareable link.
- **④ Genie Agent** with instructions and sample questions.
- **⑤ Governance, sharing and access control.**

![Architecture](docs/architecture.png)

## What's here

| Path | What it is |
|---|---|
| `pipeline/policy_layers.sql` | **The pipeline**: ruby (`policy_ruby`, the union) and diamond (`policy_diamond`, 5 columns), with column comments and expectations |
| `sql/01_explore_sources.sql` | A 5-minute look at the two sources in the SQL Editor: different column names, raw status values |
| `sql/02_metric_view.sql` | The certified metric view `policy_metrics` on the diamond table |
| `notebooks/00_Setup` … `05_Governance` | **One step-by-step notebook per module**: numbered steps for the UI, the SQL to paste, and a catch-up cell that does the step in code |
| `notebooks/06_Cleanup`, `notebooks/Run_All` | Delete your resources; run every module in order (facilitator dry run) |
| `notebooks/_config` | Shared settings (source/target tables, warehouse, group), loaded by every module notebook |
| `WORKSHOP_STEPS.md` | **Step-by-step execution guide**: admin prerequisites, UI steps per module, commands, troubleshooting |
| `docs/architecture.svg` / `.png` | The architecture, plus what must be enabled |

## Agenda (3.5 hours)

| Time | Module |
|---|---|
| 0:00–0:05 | Welcome and objectives |
| 0:05–0:15 | **Overview of Databricks**: Unity Catalog, Lakeflow pipelines, metric views, Databricks SQL, AI/BI dashboards, Genie |
| 0:15–0:45 | **1 · Layered architecture & pipeline**: a 5-minute look at the sources, then build and run the ruby → diamond pipeline in the Lakeflow Pipelines Editor; pipeline graph, expectations, schedule |
| 0:45–1:20 | **2 · After the table**: data quality, lineage and column docs in Catalog Explorer; the certified metric view `policy_metrics` |
| 1:20–1:35 | Break |
| 1:35–2:25 | **3 · AI/BI dashboard**: datasets, KPI / trend / breakdown visuals, filters and a parameter; publish and share |
| 2:25–3:00 | **4 · Genie Agent**: instructions, sample questions, example SQL; business-style questions; Monitor |
| 3:00–3:10 | Break |
| 3:10–3:30 | **5 · Governance, sharing and access control**: diamond-only grants, dashboard and Genie `CAN RUN`, embedded credentials, row-filter demo |

## What must be enabled

| Who | What |
|---|---|
| Account admin | Unity Catalog metastore · **partner-powered AI features** (Genie needs them) · cross-Geo processing if your Geo requires it · an **account-level** Entra ID group for attendees and viewers |
| Workspace admin | **Serverless pipelines** and serverless notebooks · serverless (or pro) SQL warehouse with `CAN USE` for the group · **Databricks SQL** entitlement for report developers; consumer access for viewers · UC `USE CATALOG` / `USE SCHEMA` / `SELECT` on the source tables, plus `CREATE SCHEMA` (or a schema per attendee) in the target catalog · Git folders · optionally `ASSIGN` on `system.certification_status` |
| Not needed | Databricks Apps or a separate BI tool |

## Quick start

1. In the workspace, create a **Git folder** from this repo, and attach notebooks to **Serverless** compute.
2. Open `notebooks/00_Setup` and set the widgets:
   - `source_catalog`, `source_schema`, `annuity_table`, `life_table`: where the two source tables are;
   - `target_catalog` / `target_schema`: where ruby and diamond are written (defaults to `policy_layers_<you>`);
   - `warehouse_id` and `group_name`.

   If you have no data yet, set *Synthetic data if missing* to `true`.
3. Work through the module notebooks in order:

   | Notebook | Module |
   |---|---|
   | `00_Setup` | Check the sources, create your schema |
   | `01_Layered_Pipeline` | Look at the sources, build and run the ruby → diamond pipeline, schedule it |
   | `02_After_the_Table` | Documentation, lineage, data quality, the certified metric view |
   | `03_AIBI_Dashboard` | Build, publish and share the *Policy Overview* dashboard |
   | `04_Genie_Agent` | Create the Genie Agent, ask questions, monitor |
   | `05_Governance` | Diamond-only grants, sharing, embedded credentials, row-filter demo |
   | `06_Cleanup` | Delete your resources |

   Each step says what to do in the UI. If you fall behind, run that step's **catch-up cell**.

**Facilitator dry run:** open `notebooks/Run_All`, set the same widgets, and **Run all**. About 10 minutes later you have the
pipeline, ruby and diamond tables, the metric view, a published dashboard, a Genie Agent and the grants.

`WORKSHOP_STEPS.md` has the same steps as one document, with admin prerequisites and troubleshooting.

**Your own tables:** only the two `SELECT`s in `policy_ruby` (`pipeline/policy_layers.sql`) change. Map each source
column to the ruby column names (`policy_number`, `customer_id`, `product_name`, `policy_status`, `issue_date`,
`issue_state`, `premium_amount`, `distribution_channel`) and adjust the status mapping. The diamond table, metric view,
dashboard and Genie Agent don't change.

All data in this repo is synthetic.
