"""Pulls Baseball Savant season leaderboards (running game + defense) into S3 bronze, as raw as they arrive.
One request per leaderboard, a few seconds apart. Season-level data: pull once after the season
(weekly in-season refresh is deferred; see BACKLOG.md)."""
import argparse
import time

import pandas as pd
from pybaseball import (
    statcast_catcher_poptime,
    statcast_outfield_catch_prob,
    statcast_outfielder_jump,
    statcast_outs_above_average,
    statcast_sprint_speed,
)

from src.ingest.s3_utils import write_parquet

BOARDS = {
    "sprint_speed": lambda y: statcast_sprint_speed(y, 10),
    "catcher_poptime": lambda y: statcast_catcher_poptime(y, 5, 0),
    "outs_above_average": lambda y: statcast_outs_above_average(y, "all"),
    "outfield_catch_prob": lambda y: statcast_outfield_catch_prob(y),
    "outfielder_jump": lambda y: statcast_outfielder_jump(y),
}


def run(season: int) -> None:
    pulled_at = pd.Timestamp.now(tz="UTC")
    for name, fn in BOARDS.items():
        df = fn(season)
        df["season"] = season
        df["pulled_at"] = pulled_at
        write_parquet(df, f"bronze/savant/{name}/season={season}/{name}.parquet")
        time.sleep(3)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--season", type=int, required=True)
    a = p.parse_args()
    run(a.season)
