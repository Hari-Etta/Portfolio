# E-Commerce Medallion Data Platform

Three teams, three different revenue numbers, zero trust — until there was one pipeline everyone could point to.

## Project: E-Commerce Medallion Data Platform
A bronze→silver→gold pipeline on real Olist e-commerce order data, giving every downstream team
one trusted source instead of re-deriving their own numbers. Stack: AWS S3, Databricks (PySpark),
dbt, GitHub Actions, Tableau Public.

## Status
- [x] Step 1 — Project scaffold & setup
- [ ] Step 2 — Bronze layer (raw ingestion + data quality check)
- [ ] Step 3 — Silver layer (dbt transformations + tests)
- [ ] Step 4 — Gold layer (business aggregates via PySpark)
- [ ] Step 5 — Orchestration (GitHub Actions)
- [ ] Step 6 — BI dashboard (Tableau Public)
- [ ] Step 7 — Polished landing page (portfolio integration)
- [ ] Step 8 — Final repo, resume, portfolio, LinkedIn materials

## Setup

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then fill in your real credentials
```

## Accounts you'll need (all free tier)
- AWS free tier (S3 bucket for the bronze layer)
- Databricks Community Edition (PySpark transformations)
- Tableau Public (BI dashboard)
- GitHub Pages or Netlify (landing page hosting)


# Build Progress Log

## Step 1 — Scaffold (done)
Created `ecommerce-medallion-platform/` with:
- `README.md` (status checklist for all 8 steps, setup instructions, accounts needed)
- `requirements.txt` (boto3, pyspark, dbt-databricks, pandas, python-dotenv)
- `.env.example` (AWS + Databricks placeholders)
- `data/raw/` (empty, waiting for Olist CSVs)

Delivered to user as a tar.gz via SendUserFile.

**Accounts still needed from user:** AWS free tier (S3), Databricks Community Edition, Tableau Public, GitHub Pages or Netlify.

**Next step:** Step 2 — download Olist dataset from Kaggle into data/raw/, build s3_upload.py + data_quality_check.py, run the quality check, and document real null/duplicate findings (this becomes the "before" half of the data-quality story referenced throughout the narrative).dvdv


### Bronze Layer & Data Quality
Raw Olist CSVs (customers, geolocation, orders, order_items, order_payments, order_reviews,
products, sellers, category translation) loaded as the bronze layer. Initial quality check found:
- **Geolocation: 26.2% duplicate rows** (261,831 of 1,000,163) — must dedupe before any join
- **Orders: 3.0% missing delivery date, 1.8% missing carrier-handoff date, 0.16% missing approval
  date** — consistent with canceled/in-transit orders, not data corruption
- **Reviews: 88.3% missing title, 58.7% missing comment text** — expected for optional free-text
  fields, handled via null-safe fallback rather than treated as errors
- **Products: 1.85% missing category name** (610 of 32,951 rows), 2 rows missing weight/dimensions


# Build Progress Log

## Step 1 — Scaffold (done)
Created `03-e-commerce-medallion-platform/` locally (user renamed from ecommerce-medallion-platform) with:
- `README.md`, `requirements.txt` (boto3, pyspark, dbt-databricks, pandas, python-dotenv, kaggle), `.env.example`, `data/raw/`

User is on Windows (PowerShell), working entirely locally in their own venv — all code/scripts handed to them as snippets, not executed in this cloud session.

## Step 2 — Bronze layer data quality check (done — REAL FINDINGS)
Ran `data_quality_check.py` against 9 raw Olist CSVs. Key "before" findings:
- Geolocation: 1,000,163 rows, **26.2% duplicate rows** (261,831)
- Orders: nulls in approval/carrier/delivery dates (0.16%/1.8%/3.0%) — consistent with canceled/in-transit orders
- Reviews: 88.3%/58.7% missing title/comment text — expected optional fields
- Products: 1.85% missing category name, 2 rows missing dimensions

## Git hygiene (done)
Raw CSVs (~125MB) had been committed to git history before `.gitignore` existed. Added proper `.gitignore`, then used `git filter-repo --path 03-e-commerce-medallion-platform/data/raw --invert-paths --force` to purge them from all history, re-added origin remote, force-pushed. Repo (Hari-Etta/Portfolio on GitHub) is now clean — no CSVs, no secrets, ever, in history.

## Step 3 — Silver layer: dbt on Databricks (DONE — all tests passing)
**Infra:** Databricks Free Edition workspace. Catalog `dbt-medallion` (note: hyphenated name, referenced via `database:` key in dbt sources.yml / `catalog:` in profiles.yml — dbt handles the quoting). Serverless Starter Warehouse used for SQL. All 9 raw CSVs uploaded as bronze tables under `dbt-medallion.bronze` via Catalog > Create table > Upload file.

**dbt project** lives in `dbt_projects/` locally (note: plural — differs from original guide's singular `dbt_project/`, just a naming quirk, not a bug). Env vars (DATABRICKS_HOST/TOKEN/HTTP_PATH) loaded into `.env`, with a `load_env.ps1` helper script (project root) to inject them into each new PowerShell session since dbt doesn't read `.env` natively — must be dot-sourced (`. .\load_env.ps1`) from the project root before running dbt commands.

**Real bug found and fixed (the differentiator finding):** `dbt test` initially failed 2 of 12 tests:
1. `not_null` on `silver_order_reviews.order_id` — 2,236 rows (2.25%) failed. Root cause: NOT a real data issue — Databricks' "Upload file" UI parser split raw newlines inside quoted multi-line review-comment text, shredding ~2,236 rows across the wrong columns (review text/timestamps ended up in the `review_id` column; every other column went null). This was invisible in the original Step 2 pandas-based check because pandas correctly parses quoted multi-line CSV fields — a genuinely interesting "two different tools, two different results" finding. Fixed by writing `src/ingestion/fix_reviews_csv.py` (collapses embedded `\r\n` in review text columns to spaces before upload), re-uploading the cleaned CSV to Databricks as a replacement for the bronze `olist_order_reviews_dataset` table.
2. `accepted_values` on `review_score` — 1 row had `review_score = 0`, outside Olist's valid 1-5 range. This IS a genuine data anomaly (not a parsing artifact). Fixed by adding `where review_score between 1 and 5` to `silver_order_reviews.sql`, documented in the model's header comment.

After both fixes: **`dbt test` → PASS=12, WARN=0, ERROR=0, TOTAL=12.** All 4 silver models (`silver_orders`, `silver_customers`, `silver_geolocation`, `silver_order_reviews`) built successfully in the `silver` schema under `dbt-medallion`.

**Final real README/narrative numbers to use:**
- 9 raw tables ingested, 4 silver models built, 12 dbt tests, 100% passing after 2 real issues found and fixed
- 1 CSV upload parsing bug caught and fixed (2,236 rows / 2.25% of reviews affected)
- 1 genuine data anomaly caught and fixed (1 row, review_score=0 outside valid range)
- 26.2% duplicate rows deduped in geolocation
- 88.3%/58.7% null-safe handling on review text fields

**Next step: Step 4 — Gold layer.** Build business aggregates (revenue by region, delivery performance, customer LTV) from the now-tested silver tables. Original guide used PySpark on Databricks for this; given the user is already comfortably running dbt/SQL against Databricks, worth deciding with the user whether to do gold as PySpark (per original plan, demonstrates PySpark skill for the DE/DS role coverage) or continue in dbt SQL models (faster, consistent with silver layer tooling) before writing the actual gold code.


# Build Progress Log

## Step 1 — Scaffold (done)
Created `03-e-commerce-medallion-platform/` locally (user renamed from ecommerce-medallion-platform) with:
- `README.md`, `requirements.txt` (boto3, pyspark, dbt-databricks, pandas, python-dotenv, kaggle), `.env.example`, `data/raw/`

User is on Windows (PowerShell), working entirely locally in their own venv — all code/scripts handed to them as snippets, not executed in this cloud session.

## Step 2 — Bronze layer data quality check (done — REAL FINDINGS)
Ran `data_quality_check.py` against 9 raw Olist CSVs. Key "before" findings:
- Geolocation: 1,000,163 rows, **26.2% duplicate rows** (261,831)
- Orders: nulls in approval/carrier/delivery dates (0.16%/1.8%/3.0%) — consistent with canceled/in-transit orders
- Reviews: 88.3%/58.7% missing title/comment text — expected optional fields
- Products: 1.85% missing category name, 2 rows missing dimensions

## Git hygiene (done)
Raw CSVs (~125MB) had been committed to git history before `.gitignore` existed. Added proper `.gitignore`, then used `git filter-repo --path 03-e-commerce-medallion-platform/data/raw --invert-paths --force` to purge them from all history, re-added origin remote, force-pushed. Repo (Hari-Etta/Portfolio on GitHub) is now clean — no CSVs, no secrets, ever, in history.

## Step 3 — Silver layer: dbt on Databricks (DONE — all tests passing)
**Infra:** Databricks Free Edition workspace. Catalog `dbt-medallion` (note: hyphenated name, referenced via `database:` key in dbt sources.yml / `catalog:` in profiles.yml — dbt handles the quoting). Serverless Starter Warehouse used for SQL. All 9 raw CSVs uploaded as bronze tables under `dbt-medallion.bronze` via Catalog > Create table > Upload file.

**dbt project** lives in `dbt_projects/` locally (note: plural — differs from original guide's singular `dbt_project/`, just a naming quirk, not a bug). Env vars (DATABRICKS_HOST/TOKEN/HTTP_PATH) loaded into `.env`, with a `load_env.ps1` helper script (project root) to inject them into each new PowerShell session since dbt doesn't read `.env` natively — must be dot-sourced (`. .\load_env.ps1`) from the project root before running dbt commands.

**Real bug found and fixed (the differentiator finding):** `dbt test` initially failed 2 of 12 tests:
1. `not_null` on `silver_order_reviews.order_id` — 2,236 rows (2.25%) failed. Root cause: NOT a real data issue — Databricks' "Upload file" UI parser split raw newlines inside quoted multi-line review-comment text, shredding ~2,236 rows across the wrong columns (review text/timestamps ended up in the `review_id` column; every other column went null). This was invisible in the original Step 2 pandas-based check because pandas correctly parses quoted multi-line CSV fields — a genuinely interesting "two different tools, two different results" finding. Fixed by writing `src/ingestion/fix_reviews_csv.py` (collapses embedded `\r\n` in review text columns to spaces before upload), re-uploading the cleaned CSV to Databricks as a replacement for the bronze `olist_order_reviews_dataset` table.
2. `accepted_values` on `review_score` — 1 row had `review_score = 0`, outside Olist's valid 1-5 range. This IS a genuine data anomaly (not a parsing artifact). Fixed by adding `where review_score between 1 and 5` to `silver_order_reviews.sql`, documented in the model's header comment.

After both fixes: **`dbt test` → PASS=12, WARN=0, ERROR=0, TOTAL=12.** All 4 silver models (`silver_orders`, `silver_customers`, `silver_geolocation`, `silver_order_reviews`) built successfully in the `silver` schema under `dbt-medallion`.

**Final real README/narrative numbers to use:**
- 9 raw tables ingested, 4 silver models built, 12 dbt tests, 100% passing after 2 real issues found and fixed
- 1 CSV upload parsing bug caught and fixed (2,236 rows / 2.25% of reviews affected)
- 1 genuine data anomaly caught and fixed (1 row, review_score=0 outside valid range)
- 26.2% duplicate rows deduped in geolocation
- 88.3%/58.7% null-safe handling on review text fields

**Next step: Step 4 — Gold layer.** Build business aggregates (revenue by region, delivery performance, customer LTV) from the now-tested silver tables. Original guide used PySpark on Databricks for this; given the user is already comfortably running dbt/SQL against Databricks, worth deciding with the user whether to do gold as PySpark (per original plan, demonstrates PySpark skill for the DE/DS role coverage) or continue in dbt SQL models (faster, consistent with silver layer tooling) before writing the actual gold code.