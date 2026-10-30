"""Pulls teams, 40-man rosters, and transactions from the public MLB Stats API into S3 bronze.
In Phase 4 this same module runs daily inside AWS Lambda."""
import argparse

import pandas as pd
import requests

from src.ingest.s3_utils import write_parquet

BASE = "https://statsapi.mlb.com/api/v1"


def _get(path: str, params: dict) -> dict:
    r = requests.get(f"{BASE}{path}", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def get_teams(season: int) -> pd.DataFrame:
    return pd.json_normalize(_get("/teams", {"sportId": 1, "season": season})["teams"])


def get_roster(team_id: int, season: int) -> pd.DataFrame:
    data = _get(f"/teams/{team_id}/roster", {"rosterType": "40Man", "season": season})
    df = pd.json_normalize(data.get("roster", []))
    df["team_id"] = team_id
    return df


def get_transactions(start: str, end: str) -> pd.DataFrame:
    data = _get("/transactions", {"startDate": start, "endDate": end, "sportId": 1})
    return pd.json_normalize(data.get("transactions", []))


def run(season: int, tx_start: str, tx_end: str) -> None:
    today = pd.Timestamp.now(tz="UTC").date()
    teams = get_teams(season)
    write_parquet(teams, f"bronze/mlb/teams/season={season}/teams.parquet")

    rosters = pd.concat([get_roster(t, season) for t in teams["id"]], ignore_index=True)
    rosters["snapshot_date"] = str(today)  # dated snapshots power the "what changed" feed
    write_parquet(rosters, f"bronze/mlb/rosters/snapshot_date={today}/rosters.parquet")

    tx = get_transactions(tx_start, tx_end)
    write_parquet(tx, f"bronze/mlb/transactions/pulled={today}/{tx_start}_{tx_end}.parquet")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--season", type=int, required=True)
    p.add_argument("--tx-start", required=True, help="YYYY-MM-DD")
    p.add_argument("--tx-end", required=True, help="YYYY-MM-DD")
    a = p.parse_args()
    run(a.season, a.tx_start, a.tx_end)
