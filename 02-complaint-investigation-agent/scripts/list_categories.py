"""One-off exploration to get the COMPLETE set of real category values for
columns the agent commonly filters on — used to hard-code exact values into
schema_reference.py instead of letting the agent guess plausible spellings."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from dotenv import load_dotenv
load_dotenv()
from src.data.bigquery_client import run_query

print("=== ALL product values ===")
df = run_query("""
    SELECT product, COUNT(*) as cnt
    FROM `bigquery-public-data.cfpb_complaints.complaint_database`
    GROUP BY product ORDER BY cnt DESC
""")
print(df.to_string(index=False))

print("\n=== ALL company_response_to_consumer values ===")
df2 = run_query("""
    SELECT company_response_to_consumer, COUNT(*) as cnt
    FROM `bigquery-public-data.cfpb_complaints.complaint_database`
    GROUP BY company_response_to_consumer ORDER BY cnt DESC
""")
print(df2.to_string(index=False))

print("\n=== ALL submitted_via values ===")
df3 = run_query("""
    SELECT submitted_via, COUNT(*) as cnt
    FROM `bigquery-public-data.cfpb_complaints.complaint_database`
    GROUP BY submitted_via ORDER BY cnt DESC
""")
print(df3.to_string(index=False))
