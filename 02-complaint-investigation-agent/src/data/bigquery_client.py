"""BigQuery client wrapper — the data layer the agent's SQL tool queries against.

Confirmed against the live table on 2026-09-13: `bigquery-public-data.cfpb_complaints.complaint_database`
is publicly accessible with no fallback ingestion needed.
"""
from google.cloud import bigquery
import os
import pandas as pd

TABLE_REF = "bigquery-public-data.cfpb_complaints.complaint_database"

_client = None


def get_client() -> bigquery.Client:
    """Lazily creates the BigQuery client so importing this module doesn't require
    credentials to already be configured (useful for tests that mock this out)."""
    global _client
    if _client is None:
        _client = bigquery.Client(project=os.environ["GCP_PROJECT_ID"])
    return _client


def run_query(sql: str) -> pd.DataFrame:
    """Executes a SQL query and returns results as a DataFrame. Called only after
    guardrail validation in src/tools/sql_tool.py — never call this directly with
    unvalidated, model-generated SQL."""
    return get_client().query(sql).to_dataframe()


def get_schema() -> list[dict]:
    """Returns column names/types/descriptions so the agent can ground its SQL
    generation in the real schema rather than a guessed one."""
    table = get_client().get_table(TABLE_REF)
    return [
        {"name": f.name, "type": f.field_type, "description": f.description}
        for f in table.schema
    ]