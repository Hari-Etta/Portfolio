"""Backfills running-game events from the MLB play-by-play feed into S3 bronze, one file per game date.
- Pickoff attempts: non-pitch play events whose description starts with "Pickoff Attempt".
- Stolen bases / caught stealing / successful pickoffs: runner movements by eventType.
Resumable: dates already in S3 are skipped (empty dates still get a file). ~1 request per second.
Not in the feed: pitcher step-offs without a throw, lead distances, steal timing."""
import argparse
import time

import pandas as pd
import requests

from src.ingest.s3_utils import key_exists, write_parquet

BASE = "https://statsapi.mlb.com/api"
DELAY_SECONDS = 1.0
RUNNER_EVENT_PREFIXES = ("stolen_base", "caught_stealing", "pickoff")
COLUMNS = [
    "game_pk", "game_date", "at_bat_number", "inning", "half", "pitcher_id", "batter_id",
    "source", "event_type", "base", "end_base", "runner_id", "is_out",
    "event_index", "balls", "strikes", "outs", "description",
]
INT_COLUMNS = ["game_pk", "at_bat_number", "inning", "pitcher_id", "batter_id", "runner_id",
               "event_index", "balls", "strikes", "outs"]


def _get(url: str, params: dict | None = None) -> dict:
    r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    time.sleep(DELAY_SECONDS)
    return r.json()


def game_events(game_pk: int, game_date: str) -> list[dict]:
    feed = _get(f"{BASE}/v1.1/game/{game_pk}/feed/live")
    rows = []
    for play in feed.get("liveData", {}).get("plays", {}).get("allPlays", []):
        about, matchup = play.get("about", {}), play.get("matchup", {})
        ab_index = play.get("atBatIndex")
        common = {
            "game_pk": game_pk,
            "game_date": game_date,
            "at_bat_number": ab_index + 1 if ab_index is not None else None,  # Statcast at_bat_number is 1-based
            "inning": about.get("inning"),
            "half": about.get("halfInning"),
            "pitcher_id": matchup.get("pitcher", {}).get("id"),
            "batter_id": matchup.get("batter", {}).get("id"),
        }
        for ev in play.get("playEvents", []):
            desc = (ev.get("details", {}).get("description") or "").strip()
            if ev.get("isPitch") is False and desc.lower().startswith("pickoff attempt"):
                count = ev.get("count", {})
                rows.append({**common, "source": "play_event", "event_type": "pickoff_attempt",
                             "base": desc.split()[-1], "event_index": ev.get("index"),
                             "balls": count.get("balls"), "strikes": count.get("strikes"),
                             "outs": count.get("outs"), "description": desc})
        for runner in play.get("runners", []):
            d = runner.get("details", {})
            event_type = d.get("eventType") or ""
            if event_type.startswith(RUNNER_EVENT_PREFIXES):
                move = runner.get("movement", {})
                rows.append({**common, "source": "runner", "event_type": event_type,
                             "base": move.get("originBase"), "end_base": move.get("end"),
                             "runner_id": d.get("runner", {}).get("id"), "is_out": move.get("isOut"),
                             "event_index": d.get("playIndex"), "description": d.get("event")})
    return rows


def backfill(start: str, end: str, season: int) -> None:
    for day in pd.date_range(start, end):
        date = str(day.date())
        key = f"bronze/mlb/running_game/season={season}/game_date={date}.parquet"
        if key_exists(key):
            print(f"skip {date} (already uploaded)")
            continue
        sched = _get(f"{BASE}/v1/schedule", {"sportId": 1, "date": date, "gameType": "R"})
        game_pks = [g["gamePk"] for d in sched.get("dates", []) for g in d["games"]
                    if g["status"]["detailedState"] in ("Final", "Completed Early")]
        rows = []
        for pk in game_pks:
            rows.extend(game_events(pk, date))
        df = pd.DataFrame(rows, columns=COLUMNS)
        for c in INT_COLUMNS:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")
        df["is_out"] = df["is_out"].astype("boolean")
        df["ingested_at"] = pd.Timestamp.now(tz="UTC")
        write_parquet(df, key)
        print(f"  {date}: {len(game_pks)} games, {len(df)} running-game events")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--start", required=True, help="YYYY-MM-DD")
    p.add_argument("--end", required=True, help="YYYY-MM-DD")
    p.add_argument("--season", type=int, required=True)
    a = p.parse_args()
    backfill(a.start, a.end, a.season)
