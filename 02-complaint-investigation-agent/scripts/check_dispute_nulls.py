import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from dotenv import load_dotenv
load_dotenv()
from src.data.bigquery_client import run_query

df = run_query("""
    SELECT
      COUNT(*) as total,
      COUNTIF(consumer_disputed IS NULL) as null_disputed,
      COUNTIF(consumer_disputed = TRUE) as disputed_true,
      COUNTIF(consumer_disputed = FALSE) as disputed_false
    FROM `bigquery-public-data.cfpb_complaints.complaint_database`
    WHERE product = 'Debt collection'
""")
print(df.to_string(index=False))