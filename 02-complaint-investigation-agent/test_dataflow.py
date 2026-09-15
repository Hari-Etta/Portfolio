"""Verifies the data layer works end-to-end against the live BigQuery table."""
from dotenv import load_dotenv
load_dotenv()

from src.data.bigquery_client import run_query, TABLE_REF
from src.data.schema_reference import SCHEMA_DESCRIPTION

sql = f"""
SELECT product, COUNT(*) as cnt
FROM `{TABLE_REF}`
GROUP BY product
ORDER BY cnt DESC
LIMIT 5
"""

df = run_query(sql)
print(df)
print()
print(SCHEMA_DESCRIPTION[:200])