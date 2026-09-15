"""One-off exploration script to pull real ground-truth numbers for writing
verified evaluation questions — run once, not part of the app itself."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from src.data.bigquery_client import run_query

QUERIES = {
    "top_5_products_alltime": """
        SELECT product, COUNT(*) as cnt
        FROM `bigquery-public-data.cfpb_complaints.complaint_database`
        GROUP BY product ORDER BY cnt DESC LIMIT 5
    """,
    "top_5_states": """
        SELECT state, COUNT(*) as cnt
        FROM `bigquery-public-data.cfpb_complaints.complaint_database`
        WHERE state IS NOT NULL
        GROUP BY state ORDER BY cnt DESC LIMIT 5
    """,
    "date_range": """
        SELECT MIN(date_received) as earliest, MAX(date_received) as latest
        FROM `bigquery-public-data.cfpb_complaints.complaint_database`
    """,
    "overall_timely_pct": """
        SELECT ROUND(100.0 * COUNTIF(timely_response = TRUE) / COUNT(*), 2) as pct
        FROM `bigquery-public-data.cfpb_complaints.complaint_database`
    """,
    "top_5_companies_alltime": """
        SELECT company_name, COUNT(*) as cnt
        FROM `bigquery-public-data.cfpb_complaints.complaint_database`
        GROUP BY company_name ORDER BY cnt DESC LIMIT 5
    """,
    "top_issue_for_mortgage": """
        SELECT issue, COUNT(*) as cnt
        FROM `bigquery-public-data.cfpb_complaints.complaint_database`
        WHERE product = 'Mortgage'
        GROUP BY issue ORDER BY cnt DESC LIMIT 3
    """,
    "complaints_2023_by_quarter": """
        SELECT EXTRACT(QUARTER FROM date_received) as q, COUNT(*) as cnt
        FROM `bigquery-public-data.cfpb_complaints.complaint_database`
        WHERE EXTRACT(YEAR FROM date_received) = 2023
        GROUP BY q ORDER BY q
    """,
    "disputed_pct_debt_collection": """
        SELECT ROUND(100.0 * COUNTIF(consumer_disputed = TRUE) / COUNT(*), 2) as pct
        FROM `bigquery-public-data.cfpb_complaints.complaint_database`
        WHERE product = 'Debt collection' AND consumer_disputed IS NOT NULL
    """,
    "submitted_via_breakdown": """
        SELECT submitted_via, COUNT(*) as cnt
        FROM `bigquery-public-data.cfpb_complaints.complaint_database`
        GROUP BY submitted_via ORDER BY cnt DESC
    """,
    "company_response_breakdown": """
        SELECT company_response_to_consumer, COUNT(*) as cnt
        FROM `bigquery-public-data.cfpb_complaints.complaint_database`
        GROUP BY company_response_to_consumer ORDER BY cnt DESC
    """,
}

for name, sql in QUERIES.items():
    print(f"\n=== {name} ===")
    try:
        df = run_query(sql)
        print(df.to_string(index=False))
    except Exception as e:
        print(f"FAILED: {e}")