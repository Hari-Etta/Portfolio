"""AWS Lambda entry point: daily pull of rosters (dated snapshot) and recent transactions into S3 bronze.
Triggered every morning by EventBridge Scheduler. Reuses the tested mlb_api.run().
Transactions cover the last 3 days on purpose (catches up a missed day); gold_transactions deduplicates.
Manual reruns can override via the event: {"season": 2026, "tx_start": "YYYY-MM-DD", "tx_end": "YYYY-MM-DD"}."""
from datetime import datetime, timedelta, timezone

from src.ingest import mlb_api

LOOKBACK_DAYS = 3


def handler(event, context):
    event = event or {}
    today = datetime.now(timezone.utc).date()
    season = int(event.get("season", today.year))
    tx_start = event.get("tx_start", str(today - timedelta(days=LOOKBACK_DAYS)))
    tx_end = event.get("tx_end", str(today))

    print(f"daily pull: season={season} transactions {tx_start}..{tx_end}")
    mlb_api.run(season, tx_start, tx_end)
    return {"status": "ok", "season": season, "tx_start": tx_start, "tx_end": tx_end}
