"""Quick smoke test: confirms BigQuery and Gemini credentials both work."""
from dotenv import load_dotenv
load_dotenv()

import os

print("=== Checking environment variables ===")
for var in ["GOOGLE_APPLICATION_CREDENTIALS", "GCP_PROJECT_ID", "ANTHROPIC_API_KEY"]:
    val = os.environ.get(var)
    print(f"{var}: {'SET' if val else 'MISSING'}")

print("\n=== Testing BigQuery connection ===")
try:
    from google.cloud import bigquery
    client = bigquery.Client(project=os.environ["GCP_PROJECT_ID"])
    query = "SELECT 1 AS test_value"
    result = list(client.query(query).result())
    print(f"BigQuery OK — got: {result[0].test_value}")
except Exception as e:
    print(f"BigQuery FAILED: {e}")

print("\n=== Testing Claude connection ===")
try:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=20,
        messages=[{"role": "user", "content": "Say 'hello, agent' and nothing else."}]
    )
    print(f"Claude OK — got: {message.content[0].text.strip()}")
except Exception as e:
    print(f"Claude FAILED: {e}")

print("\n=== Checking CFPB public dataset access ===")
try:
    from google.cloud import bigquery
    client = bigquery.Client(project=os.environ["GCP_PROJECT_ID"])
    query = """
    SELECT table_name
    FROM `bigquery-public-data.cfpb_complaints.INFORMATION_SCHEMA.TABLES`
    """
    tables = list(client.query(query).result())
    print("Tables found:", [row.table_name for row in tables])
except Exception as e:
    print(f"CFPB dataset check FAILED: {e}")

print("\n=== Fetching real CFPB table schema ===")
try:
    table = client.get_table("bigquery-public-data.cfpb_complaints.complaint_database")
    for field in table.schema:
        print(f"{field.name} ({field.field_type}) - {field.description}")
except Exception as e:
    print(f"Schema fetch FAILED: {e}")