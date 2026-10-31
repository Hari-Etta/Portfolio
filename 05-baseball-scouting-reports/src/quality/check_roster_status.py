"""Explains 40-man roster sizes: counts players by roster status per snapshot date.
Open question from Phase 1: some '40-man' rosters show up to 51 players."""
import os

import duckdb
from dotenv import load_dotenv

load_dotenv()
con = duckdb.connect()
con.execute("INSTALL httpfs; LOAD httpfs;")
con.execute(f"""
    CREATE SECRET s3_secret (
        TYPE S3,
        KEY_ID '{os.environ["AWS_ACCESS_KEY_ID"]}',
        SECRET '{os.environ["AWS_SECRET_ACCESS_KEY"]}',
        REGION '{os.environ.get("AWS_REGION", "us-east-2")}'
    );
""")
ROSTERS = (f"read_parquet('s3://{os.environ['S3_BUCKET']}/bronze/mlb/rosters/snapshot_date=*/*.parquet', "
           "hive_partitioning=true, union_by_name=true)")

print("=== players by roster status (latest snapshot) ===")
print(con.execute(f"""
    SELECT "status.code" AS code, "status.description" AS status, COUNT(*) AS players
    FROM {ROSTERS}
    WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM {ROSTERS})
    GROUP BY 1, 2 ORDER BY 3 DESC
""").df().to_string(index=False))

print("\n=== largest rosters: active vs other statuses (latest snapshot) ===")
print(con.execute(f"""
    SELECT team_id, COUNT(*) AS total,
           SUM(CASE WHEN "status.code" = 'A' THEN 1 ELSE 0 END) AS active,
           COUNT(*) - SUM(CASE WHEN "status.code" = 'A' THEN 1 ELSE 0 END) AS other_status
    FROM {ROSTERS}
    WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM {ROSTERS})
    GROUP BY 1 ORDER BY total DESC LIMIT 8
""").df().to_string(index=False))

print("\n=== max ACTIVE players on any team, per snapshot (should be <= 40) ===")
print(con.execute(f"""
    SELECT snapshot_date, MAX(active) AS max_active, MAX(total) AS max_total
    FROM (
        SELECT snapshot_date, team_id, COUNT(*) AS total,
               SUM(CASE WHEN "status.code" = 'A' THEN 1 ELSE 0 END) AS active
        FROM {ROSTERS} GROUP BY 1, 2
    )
    GROUP BY 1 ORDER BY 1
""").df().to_string(index=False))
