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