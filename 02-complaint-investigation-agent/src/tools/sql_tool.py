"""The guardrailed SQL execution tool — the project's core differentiator.

Nothing runs against BigQuery without passing a safety check first. Most tutorial
agents skip this and just execute whatever SQL the model generates; here every
query is validated as a read-only SELECT with no destructive keywords before it
is ever sent to BigQuery.
"""
from src.data.bigquery_client import run_query
import re
import json

# Any of these keywords appearing as a whole word anywhere in the query blocks it,
# even inside a supposedly-safe SELECT (defense in depth against injection via
# subqueries, CTEs, or multi-statement strings).
BLOCKED_KEYWORDS = [
    "DELETE", "DROP", "UPDATE", "INSERT", "ALTER",
    "TRUNCATE", "MERGE", "CREATE", "GRANT", "REVOKE",
]

MAX_ROWS = 1000  # hard cap so a runaway aggregation can't blow up the response


def validate_query(sql: str) -> tuple[bool, str]:
    """Blocks any query containing a destructive/write keyword and requires the
    query to be a read-only SELECT. Returns (is_valid, message)."""
    if not sql or not sql.strip():
        return False, "Blocked: empty query"

    upper_sql = sql.upper()

    for keyword in BLOCKED_KEYWORDS:
        if re.search(rf"\b{keyword}\b", upper_sql):
            return False, f"Blocked: query contains disallowed keyword '{keyword}'"

    # Strip leading whitespace/comments to find the real first statement
    stripped = re.sub(r"^\s*(--[^\n]*\n|\s)*", "", sql).strip()
    if not stripped.upper().startswith("SELECT") and not stripped.upper().startswith("WITH"):
        return False, "Blocked: only SELECT (or WITH ... SELECT) queries are permitted"

    # Block multiple statements (a semicolon followed by more non-whitespace content)
    if re.search(r";\s*\S", sql):
        return False, "Blocked: multiple statements are not permitted"

    return True, "OK"


def execute_sql_tool(sql: str) -> dict:
    """Tool entry point the agent calls. Validates before executing — never skip
    this step, and never call src.data.bigquery_client.run_query directly with
    unvalidated, model-generated SQL."""
    is_valid, message = validate_query(sql)
    if not is_valid:
        return {"error": message, "sql": sql}

    try:
        df = run_query(sql)
        truncated = len(df) > MAX_ROWS
        if truncated:
            df = df.head(MAX_ROWS)
        # Route through DataFrame.to_json() rather than to_dict() — BigQuery results
        # carry numpy/pandas dtypes (int64, Timestamp, etc.) that json.dumps() can't
        # serialize on their own; to_json() converts them to plain JSON types first,
        # which matters once these results get passed to the LLM or the Streamlit UI.
        records = json.loads(df.to_json(orient="records", date_format="iso"))
        return {
            "result": records,
            "row_count": len(df),
            "truncated": truncated,
            "sql": sql,
        }
    except Exception as e:
        return {"error": str(e), "sql": sql}