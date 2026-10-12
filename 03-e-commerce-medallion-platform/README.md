# E-Commerce Medallion Data Platform

> Three teams, three different revenue numbers, zero trust — until there was one pipeline everyone could point to.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Databricks](https://img.shields.io/badge/Databricks-PySpark-FF3621?logo=databricks&logoColor=white)
![dbt](https://img.shields.io/badge/dbt-transformations%20%2B%20tests-FF694B?logo=dbt&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-2088FF?logo=githubactions&logoColor=white)
![Tableau](https://img.shields.io/badge/BI-Tableau%20Public-E97627?logo=tableau&logoColor=white)
![Status](https://img.shields.io/badge/status-active-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)

Marketing, finance, and ops at a growing e-commerce company each pulled "revenue by region" from their own spreadsheet, re-cleaning the same raw order data their own way — and the numbers never matched. This project builds one medallion data pipeline (bronze → silver → gold) on real e-commerce order data, with automated data-quality tests baked into every layer, so every downstream team and dashboard reads from the same trusted, tested source instead of re-deriving their own numbers.

**[Live Dashboard](#)** · **[GitHub Actions Run History](#)** · **[Portfolio Site](#)**
*(links go live once Steps 6–7 are published — see [Status](#status))*

---

## Table of Contents
- [Status](#status)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Data Quality — Before and After](#data-quality--before-and-after)
- [Business Findings](#business-findings)
- [Orchestration](#orchestration)
- [Dashboard](#dashboard)
- [Running This Yourself](#running-this-yourself)
- [Accounts Used](#accounts-used-all-free-tier)
- [License](#license)

---

## Status

| Step | Description | Status |
|---|---|---|
| 1 | Project scaffold & setup | ✅ Done |
| 2 | Bronze layer (raw ingestion + data quality check) | ✅ Done |
| 3 | Silver layer (dbt transformations + tests) | ✅ Done — 14/14 tests passing |
| 4 | Gold layer (business aggregates via PySpark on Databricks) | ✅ Done |
| 5 | Orchestration (GitHub Actions) | ✅ Done — daily cron + manual trigger, fully verified end-to-end |
| 6 | BI dashboard (Tableau Public Desktop) | ✅ Built — publishing to Tableau Public pending |
| 7 | Polished landing page (portfolio integration) | ⬜ Not started |
| 8 | Final repo, resume, portfolio, LinkedIn materials | ⬜ Not started |

---

## Architecture

Built on the real ~100K-order [Olist Brazilian E-Commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) (Kaggle).

```
┌─────────────────┐     ┌──────────────────────┐     ┌───────────────────────┐     ┌──────────────────────┐
│   Raw Olist      │     │  BRONZE               │     │  SILVER                │     │  GOLD                 │
│   CSVs (9 files)  │────▶│  dbt-medallion.bronze │────▶│  dbt-medallion.silver  │────▶│  dbt-medallion.gold   │
│   orders,         │     │  raw tables,          │     │  5 dbt models,         │     │  3 PySpark aggregates │
│   customers,       │     │  loaded as-is into    │     │  cleaned + deduped +   │     │  revenue_by_region,   │
│   payments,        │     │  Databricks Unity     │     │  typed, 14 dbt tests   │     │  delivery_performance,│
│   reviews,         │     │  Catalog              │     │  (unique/not_null/     │     │  customer_ltv         │
│   products, ...    │     │                       │     │  accepted_values)      │     │                       │
└─────────────────┘     └──────────────────────┘     └───────────────────────┘     └──────────┬────────────┘
                                                                                                  │
                          ┌────────────────────────────────────────────────────────────────────┘
                          ▼
                 ┌─────────────────────┐          ┌─────────────────────────┐
                 │  GitHub Actions      │          │  Tableau Public Desktop  │
                 │  daily cron + manual │ ───────▶ │  (live connection to     │
                 │  dbt run/test +      │          │  Databricks gold tables) │
                 │  triggers gold job   │          │  → dashboard → landing   │
                 │  via Databricks      │          │  page (Step 7)           │
                 │  Jobs API            │          └─────────────────────────┘
                 └─────────────────────┘
```

- **Bronze**: 9 raw Olist CSVs loaded directly into Databricks Unity Catalog (`dbt-medallion.bronze`). *(The original plan routed raw files through AWS S3 first — that step was dropped to keep the pipeline focused on Databricks + dbt + orchestration, which is where the actual engineering work lives.)*
- **Silver**: dbt models (catalog `dbt-medallion`, Serverless SQL Warehouse) clean, dedupe, and type the bronze tables — 5 models (`silver_orders`, `silver_customers`, `silver_geolocation`, `silver_order_reviews`, `silver_order_payments`), with automated dbt tests enforced on every model.
- **Gold**: a PySpark notebook on Databricks (wrapped in a Databricks Job, triggered via the Jobs API) builds three business-ready aggregate tables from tested silver data — never bronze directly, keeping the medallion contract honest.
- **Orchestration**: GitHub Actions runs the full pipeline daily (`dbt run` + `dbt test`, then triggers the gold-layer Databricks Job), plus supports manual runs via `workflow_dispatch`.
- **BI layer**: Tableau Public Desktop, connected live to the Databricks gold tables via ODBC, feeding a 3-view dashboard embedded in a custom landing page (Step 7).

**Tech stack:** Databricks (PySpark + Unity Catalog + Serverless SQL Warehouse) · dbt (dbt-databricks) · GitHub Actions · Tableau Public

---

## Project Structure

```
03-e-commerce-medallion-platform/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── data/
│   └── raw/                        # Olist CSVs (gitignored, not committed)
├── src/
│   └── ingestion/
│       ├── data_quality_check.py   # bronze-layer "before" quality check
│       └── fix_reviews_csv.py      # fixes the CSV-upload parsing bug (see Data Quality)
├── dbt_projects/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   └── models/
│       └── silver/
│           ├── sources.yml
│           ├── schema.yml          # dbt tests live here
│           ├── silver_orders.sql
│           ├── silver_customers.sql
│           ├── silver_geolocation.sql
│           ├── silver_order_reviews.sql
│           └── silver_order_payments.sql
├── load_env.ps1                    # loads .env into the PowerShell session for dbt
└── .github/
    └── workflows/
        └── run_pipeline.yml        # daily + manual orchestration
```

*(The gold-layer PySpark code lives as a Databricks notebook, not a local file — PySpark needs Databricks' Spark runtime, so it's authored and run directly in the Databricks workspace, wrapped in Databricks Job ID `28045561258563`.)*

---

## Data Quality — Before and After

A real, documented before/after — not a claim that the data arrived clean.

### Bronze layer (raw, before any cleaning)
| Table | Finding |
|---|---|
| Geolocation | **26.2% duplicate rows** (261,831 of 1,000,163) |
| Orders | Small % missing delivery (3.0%), carrier-handoff (1.8%), approval (0.16%) dates — consistent with canceled/in-transit orders, not corruption |
| Reviews | **88.3%** missing title, **58.7%** missing comment text — expected for optional free-text fields |
| Products | **1.85%** missing category name (610 of 32,951 rows) |

### Silver layer (after dbt transformations): 14/14 dbt tests passing

Getting there surfaced two real, genuine issues:

1. **CSV upload parsing bug.** Databricks' file-upload UI mis-parsed multi-line review text in the raw reviews CSV (unescaped newlines inside quoted fields), null-shredding **2,236 rows (2.25%)** of the reviews table. This was invisible to the original pandas-based bronze check, since pandas correctly handles quoted multi-line CSV fields — a genuinely interesting "two tools, two different results" finding. Fixed with `src/ingestion/fix_reviews_csv.py`, which collapses embedded newlines in the review-text columns before re-upload.
2. **Genuine data anomaly**: 1 row had `review_score = 0`, outside Olist's valid 1–5 range. Filtered out in `silver_order_reviews.sql`, documented inline.

### Gold layer anomaly (verified via direct SQL query)

Delivery-performance analysis surfaced that **6 of 625 "canceled" orders have a non-null delivery date**, averaging 20.3 days:

```sql
select order_status, count(*) as order_count,
       count(delivered_ts) as has_delivered_date,
       avg(datediff(delivered_ts, purchase_ts)) as avg_days
from `dbt-medallion`.silver.silver_orders
group by order_status order by order_count desc;
```

| order_status | order_count | has_delivered_date | avg_days |
|---|---|---|---|
| delivered | 96,478 | 96,470 | 12.50 |
| canceled | 625 | **6** | **20.33** |
| shipped / unavailable / invoiced / processing / created / approved | 2,338 (combined) | 0 | null |

These 6 orders were actually delivered to the customer and *then* marked canceled afterward — likely a return, refund, or dispute processed post-delivery, with the status field reflecting final state rather than the original delivery event. A real, explainable data quirk, confirmed by query — not a pipeline bug.

---

## Business Findings

- **Revenue is heavily concentrated in São Paulo.** SP generated ~R$5,996,050 across 41,730 orders — more than 2.8x the next-highest state, Rio de Janeiro (~R$2,142,349 / 12,839 orders).
- **Delivered orders average 12.5 days**; the 6 mis-flagged "canceled but delivered" orders averaged 20.3 days.
- **Customer lifetime value follows a steep long tail.** The vast majority of customers (~80,000) have a lifetime value under $500 — Olist's base is overwhelmingly one-time purchasers, not repeat customers, with a small minority driving outsized value up to ~$14,000.

---

## Orchestration

`.github/workflows/run_pipeline.yml` runs the full pipeline daily (6am UTC) and on manual dispatch:
1. `dbt run --profiles-dir .` and `dbt test --profiles-dir .` against Databricks
2. Calls the Databricks Jobs API (`POST /api/2.1/jobs/run-now`) to trigger the gold-layer notebook job, with explicit HTTP status checking so a silent failure can't pass as a success

Fully verified end-to-end — real GitHub Actions run history, confirmed job execution in Databricks.

---

## Dashboard

Three Tableau views built directly against the live gold tables in Databricks:

1. **Revenue by Region** — map sized/colored by total revenue, confirming São Paulo's dominance
2. **Delivery Performance by Order Status** — bar chart with the canceled-orders-with-delivery-date anomaly annotated directly on the chart
3. **Customer Lifetime Value Distribution** — histogram showing the long-tail, one-time-buyer pattern

*(Screenshot and live embed link added in Step 7, once published to Tableau Public.)*

---

## Running This Yourself

```bash
# 1. Clone and set up the environment
git clone https://github.com/Hari-Etta/Portfolio.git
cd Portfolio/03-e-commerce-medallion-platform
python -m venv venv && venv\Scripts\Activate.ps1   # Windows PowerShell
pip install -r requirements.txt
cp .env.example .env   # fill in your Databricks host/token/http_path

# 2. Load env vars into your shell (dbt doesn't read .env natively)
. .\load_env.ps1

# 3. Build and test the silver layer
cd dbt_projects
dbt run --profiles-dir .
dbt test --profiles-dir .

# 4. Run the gold layer
# Open the `gold_aggregates` notebook in your Databricks workspace and run it,
# or trigger the wrapping Databricks Job directly via the Jobs API.
```

You'll need your own Databricks workspace with the 9 raw Olist CSVs loaded as bronze tables (Catalog Explorer → Create Table → Upload File) before step 3 will work.

---

## Accounts Used (all free tier)
- Databricks Free Edition (Unity Catalog, Serverless SQL Warehouse, PySpark, Jobs API)
- Tableau Public Desktop (BI dashboard)
- GitHub Actions (orchestration, included with any GitHub repo)
- GitHub Pages or Netlify (landing page hosting, Step 7)

---

## License

MIT — see [LICENSE](LICENSE).