"""Home: pick the opponent, see its pitchers and hitters, and what changed on its roster recently."""
import pandas as pd
import streamlit as st

from lib.data import backend, load

# Roster moves that change who is available (leaves out noise such as jersey-number changes).
RELEVANT_TYPES = [
    "Status Change", "Optioned", "Recalled", "Selected", "Trade", "Designated for Assignment",
    "Claimed Off Waivers", "Released", "Outrighted", "Signed", "Signed as Free Agent",
    "Declared Free Agency", "Acquired",
]

st.title("⚾ Advance Scouting Reports")
st.caption(f"2026 MLB regular season · data backend: {backend()}")

players = load("players")
teams = load("teams")
names = dict(zip(teams["abbreviation"], teams["name"]))
abbrs = sorted(a for a in players["last_team"].dropna().unique() if a in names)

default = st.session_state.get("team", abbrs[0])
team = st.selectbox(
    "Opponent team",
    abbrs,
    index=abbrs.index(default) if default in abbrs else 0,
    format_func=lambda a: f"{a} · {names.get(a, a)}",
)
st.session_state["team"] = team
team_id = int(teams.loc[teams["abbreviation"] == team, "team_id"].iloc[0])
display = players[["player_id", "display_name"]]

left, right = st.columns(2)
with left:
    st.subheader("Pitchers")
    ars = load("pitcher_arsenal")
    p = (ars[ars["last_team"] == team]
         .groupby("pitcher_id", as_index=False)["pitches"].sum()
         .merge(display, left_on="pitcher_id", right_on="player_id")
         .sort_values("pitches", ascending=False))
    st.dataframe(p[["display_name", "pitches"]].rename(columns={"display_name": "Pitcher", "pitches": "Pitches"}),
                 hide_index=True, width="stretch", height=300)
    st.page_link("pages/pitcher.py", label="Open pitcher report", icon="🎯")

with right:
    st.subheader("Hitters")
    hs = load("hitter_splits")
    h = (hs[hs["last_team"] == team]
         .groupby("batter_id", as_index=False)["pa"].sum()
         .merge(display, left_on="batter_id", right_on="player_id")
         .sort_values("pa", ascending=False))
    st.dataframe(h[["display_name", "pa"]].rename(columns={"display_name": "Hitter", "pa": "PA"}),
                 hide_index=True, width="stretch", height=300)
    st.page_link("pages/hitter.py", label="Open hitter report", icon="🏏")

st.subheader("What changed")
tx = load("transactions").copy()
tx["transaction_date"] = pd.to_datetime(tx["transaction_date"])
days = st.slider("Show the last N days", min_value=7, max_value=120, value=30, step=1)
cutoff = tx["transaction_date"].max() - pd.Timedelta(days=days)
recent = tx[
    ((tx["to_team_id"] == team_id) | (tx["from_team_id"] == team_id))
    & tx["type_desc"].isin(RELEVANT_TYPES)
    & (tx["transaction_date"] >= cutoff)
].sort_values("transaction_date", ascending=False)

if recent.empty:
    st.info(f"No roster moves for {team} in the last {days} days.")
else:
    st.dataframe(
        recent[["transaction_date", "type_desc", "player_name", "description"]].rename(columns={
            "transaction_date": "Date", "type_desc": "Move", "player_name": "Player", "description": "Details"}),
        hide_index=True, width="stretch",
        column_config={"Date": st.column_config.DateColumn(format="MMM D, YYYY")},
    )
    st.caption(f"{len(recent)} roster moves since {cutoff:%b %d, %Y}. Jersey-number changes and other non-roster moves are hidden.")
