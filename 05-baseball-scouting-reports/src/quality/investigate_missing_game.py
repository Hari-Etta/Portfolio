"""Investigation: the full 2026 pull has 2,429 games, but a full season is 2,430.
Compares Statcast game IDs against the official MLB schedule to find the gap."""
import os

import duckdb
import pandas as pd
import requests
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
SRC = (f"read_parquet('s3://{os.environ['S3_BUCKET']}/bronze/statcast/season=*/*.parquet', "
       "union_by_name=true, hive_partitioning=true)")

# 1. Which teams don't have 162 games in our Statcast data?
per_team = con.execute(f"""
    WITH g AS (SELECT DISTINCT game_pk, home_team, away_team FROM {SRC}),
    t AS (SELECT home_team AS team, game_pk FROM g
          UNION ALL SELECT away_team AS team, game_pk FROM g)
    SELECT team, COUNT(DISTINCT game_pk) AS games
    FROM t GROUP BY 1 HAVING COUNT(DISTINCT game_pk) <> 162 ORDER BY 1
""").df()
print("=== teams without 162 games in Statcast ===")
print(per_team.to_string(index=False) if not per_team.empty else "none")

statcast_pks = set(con.execute(f"SELECT DISTINCT CAST(game_pk AS BIGINT) FROM {SRC}").df().iloc[:, 0])

# 2. Official regular-season schedule from the MLB Stats API
r = requests.get(
    "https://statsapi.mlb.com/api/v1/schedule",
    params={"sportId": 1, "season": 2026, "gameType": "R",
            "startDate": "2026-03-01", "endDate": "2026-10-31"},
    timeout=60,
)
r.raise_for_status()
rows = []
for d in r.json()["dates"]:
    for g in d["games"]:
        rows.append({
            "game_pk": g["gamePk"],
            "date": g.get("officialDate", d["date"]),
            "away": g["teams"]["away"]["team"]["name"],
            "home": g["teams"]["home"]["team"]["name"],
            "status": g["status"]["detailedState"],
        })
sched = pd.DataFrame(rows)

print("\n=== official schedule: distinct regular-season games ===")
print(sched["game_pk"].nunique())
print("\n=== schedule entries by status ===")
print(sched["status"].value_counts().to_string())

# 3. Games in the schedule but missing from our Statcast data
missing = sched[~sched["game_pk"].isin(statcast_pks)].drop_duplicates()
print("\n=== in schedule, missing from Statcast ===")
print(missing.to_string(index=False) if not missing.empty else "none")

# 4. Games in Statcast but not in the schedule (should be none)
extra = statcast_pks - set(sched["game_pk"])
print("\n=== in Statcast, not in schedule ===")
print(sorted(extra) if extra else "none")
