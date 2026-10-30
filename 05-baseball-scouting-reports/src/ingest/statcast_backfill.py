"""Backfills pitch-level Statcast data week by week into the S3 bronze layer.
Weekly chunks keep requests small (Baseball Savant limits large pulls); chunks already in S3
are skipped, so reruns after a failure resume where they stopped."""
import argparse

import pandas as pd
from pybaseball import cache, statcast

from src.ingest.s3_utils import key_exists, write_parquet

cache.enable()


def backfill(start: str, end: str, season: int) -> None:
    for ws in pd.date_range(start=start, end=end, freq="7D"):
        we = min(ws + pd.Timedelta(days=6), pd.Timestamp(end))
        key = f"bronze/statcast/season={season}/week_start={ws.date()}.parquet"
        if key_exists(key):
            print(f"skip {key} (already uploaded)")
            continue
        df = statcast(start_dt=str(ws.date()), end_dt=str(we.date()))
        if df is None or df.empty:
            print(f"no games {ws.date()} to {we.date()}")
            continue
        df["ingested_at"] = pd.Timestamp.now(tz="UTC")
        write_parquet(df, key)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--start", required=True, help="Opening Day, YYYY-MM-DD")
    p.add_argument("--end", required=True, help="Last game date you want, YYYY-MM-DD")
    p.add_argument("--season", type=int, required=True)
    a = p.parse_args()
    backfill(a.start, a.end, a.season)
