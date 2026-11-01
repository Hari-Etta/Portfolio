"""Shared roster-status labels (latest daily 40-man snapshot) so every page shows status the same way."""
import pandas as pd

from lib.data import load


def status_text(r, team: str) -> str:
    if r["on_40_man"] and r["roster_team"] != team:
        return f"🔁 Now with {r['roster_team']}"
    if r["status_label"] == "Active (40-man)":
        return "✅ Active"
    if r["status_label"] == "60-day IL":
        return "🩹 60-day IL"
    if r["on_40_man"]:
        return f"🟡 {r['status_label']}"
    if pd.notna(r["last_move"]):
        return f"⚠️ {r['last_move']} ({pd.to_datetime(r['last_move_date']):%b %d})"
    return "⚠️ Not on 40-man"


def add_status(df: pd.DataFrame, id_col: str, team: str) -> pd.DataFrame:
    """Adds a 'Status' column to df by joining the current roster on id_col."""
    roster = load("current_roster").copy()
    roster["Status"] = roster.apply(lambda r: status_text(r, team), axis=1)
    return df.merge(roster[["player_id", "Status"]], left_on=id_col, right_on="player_id", how="left")


def snapshot_caption() -> str:
    roster = load("current_roster")
    return f"Roster status as of {pd.to_datetime(roster['snapshot_date'].max()):%b %d, %Y} (updated daily)."
