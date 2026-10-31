"""The ONLY place that knows where the app's data lives.
DATA_BACKEND (Streamlit secret): "s3" now (read-only AWS key); "motherduck" is the planned fallback when the
AWS free plan ends (see BACKLOG.md). Pages ask for gold tables by name; only allow-listed names are accepted."""
import duckdb
import pandas as pd
import streamlit as st

GOLD_TABLES = {
    "players", "teams", "pitcher_arsenal", "pitcher_usage_by_count", "pitcher_locations", "pitcher_platoon",
    "pitcher_spray_allowed", "pitcher_form", "pitcher_whiff_over_expected", "pitcher_running_game",
    "hitter_splits", "hitter_vs_pitch_type", "hitter_zones", "hitter_swing_decisions", "hitter_bat_tracking",
    "hitter_spray", "hitter_situational", "hitter_form", "runner_running_game", "catcher_defense",
    "fielder_defense", "player_home_road", "run_expectancy", "transactions",
}


def backend() -> str:
    return st.secrets.get("DATA_BACKEND", "s3")


@st.cache_resource
def _connection() -> duckdb.DuckDBPyConnection:
    if backend() != "s3":
        raise NotImplementedError("Only the 's3' backend is implemented so far (MotherDuck is the planned fallback).")
    aws = st.secrets["aws"]
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute(f"""
        CREATE SECRET app_s3 (
            TYPE S3,
            KEY_ID '{aws["access_key_id"]}',
            SECRET '{aws["secret_access_key"]}',
            REGION '{aws["region"]}'
        );
    """)
    return con


@st.cache_data(ttl=6 * 3600, show_spinner="Loading data...")
def load(table: str) -> pd.DataFrame:
    """Returns a gold table as a DataFrame (cached 6 hours, so the daily refresh shows up the same day)."""
    if table not in GOLD_TABLES:
        raise ValueError(f"unknown table: {table}")
    path = f"s3://{st.secrets['aws']['bucket']}/gold/{table}.parquet"
    return _connection().execute(f"SELECT * FROM read_parquet('{path}')").df()

