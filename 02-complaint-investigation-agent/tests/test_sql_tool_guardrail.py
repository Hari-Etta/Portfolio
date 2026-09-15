"""Verifies the guardrail actually blocks what it claims to block — this is the
project's key differentiator, so it needs real test coverage, not just a demo."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.tools.sql_tool import validate_query

SAFE_QUERIES = [
    "SELECT product, COUNT(*) FROM t GROUP BY product",
    "  select * from t where state = 'CA'  ",
    "WITH sub AS (SELECT * FROM t) SELECT * FROM sub",
    "-- a comment\nSELECT 1",
]

UNSAFE_QUERIES = [
    "DELETE FROM t WHERE 1=1",
    "DROP TABLE t",
    "UPDATE t SET product='x'",
    "INSERT INTO t VALUES (1)",
    "ALTER TABLE t ADD COLUMN x INT",
    "TRUNCATE TABLE t",
    "MERGE INTO t USING s ON t.id=s.id WHEN MATCHED THEN DELETE",
    "SELECT * FROM t; DROP TABLE t;",
    "CREATE TABLE t2 AS SELECT * FROM t",
    "",
    "   ",
    "just some text, not sql at all",
]


def run():
    failures = []

    for q in SAFE_QUERIES:
        ok, msg = validate_query(q)
        if not ok:
            failures.append(f"SAFE query wrongly blocked: {q!r} -> {msg}")

    for q in UNSAFE_QUERIES:
        ok, msg = validate_query(q)
        if ok:
            failures.append(f"UNSAFE query wrongly allowed: {q!r}")

    if failures:
        print(f"FAILED: {len(failures)} case(s)")
        for f in failures:
            print(" -", f)
        sys.exit(1)
    else:
        print(f"PASSED: {len(SAFE_QUERIES)} safe queries allowed, {len(UNSAFE_QUERIES)} unsafe queries blocked")


if __name__ == "__main__":
    run()