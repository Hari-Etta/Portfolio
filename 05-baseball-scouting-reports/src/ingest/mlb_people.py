"""Looks up every player in the season's Statcast data (pitchers and batters) in the MLB Stats API
and saves their official profile (name, primary position, handedness) to S3 bronze.
Used to flag position players who pitched, and to give reports real player names."""
import argparse
import os

import duckdb
import pandas as pd
import requests
from dotenv import load_dotenv

from src.ingest.s3_utils import write_parquet

load_dotenv()
BASE = "https://statsapi.mlb.com/api/v1"
BATCH = 100  # player IDs per API call


def player_ids(season: int) -> list[int]:
    """Distinct pitcher and batter IDs from bronze Statcast (ingestion never reads dbt output)."""
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
    src = (f"read_parquet('s3://{os.environ['S3_BUCKET']}/bronze/statcast/season={season}/*.parquet', "
           "union_by_name=true)")
    df = con.execute(f"""
        SELECT CAST(pitcher AS BIGINT) AS id FROM {src}
        UNION
        SELECT CAST(batter AS BIGINT) AS id FROM {src}
    """).df()
    return sorted(int(x) for x in df["id"].dropna())


def fetch_people(ids: list[int]) -> pd.DataFrame:
    rows = []
    for i in range(0, len(ids), BATCH):
        chunk = ids[i:i + BATCH]
        r = requests.get(f"{BASE}/people", params={"personIds": ",".join(map(str, chunk))}, timeout=30)
        r.raise_for_status()
        rows.extend(r.json().get("people", []))
    return pd.json_normalize(rows)


def run(season: int) -> None:
    ids = player_ids(season)
    people = fetch_people(ids)
    people["season"] = season
    people["pulled_at"] = pd.Timestamp.now(tz="UTC")
    write_parquet(people, f"bronze/mlb/people/season={season}/people.parquet")

    missing = set(ids) - set(people["id"].astype(int))
    print(f"requested {len(ids):,} player IDs, received {len(people):,} profiles, missing {len(missing)}")
    print("\nprimary position types:")
    print(people["primaryPosition.type"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--season", type=int, required=True)
    a = p.parse_args()
    run(a.season)
