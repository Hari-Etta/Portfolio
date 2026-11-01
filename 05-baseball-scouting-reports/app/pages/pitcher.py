"""Pitcher report, part 1: picker, header, arsenal, movement, usage by count."""
import pandas as pd
import plotly.express as px
import streamlit as st

from lib.charts import movement_chart, name_colors
from lib.data import load

st.title("🎯 Pitcher report")
team = st.session_state.get("team")
if team is None:
    st.info("Pick an opponent team on the Home page first.")
    st.page_link("pages/home.py", label="Go to Home", icon="🏠")
    st.stop()

players = load("players")
roster = load("current_roster").set_index("player_id")
ars = load("pitcher_arsenal")

team_ars = ars[ars["last_team"] == team]
pitchers = (team_ars.groupby("pitcher_id", as_index=False)["pitches"].sum()
            .merge(players[["player_id", "display_name", "throws"]], left_on="pitcher_id", right_on="player_id")
            .sort_values("pitches", ascending=False))
ids = pitchers["pitcher_id"].tolist()
labels = dict(zip(pitchers["pitcher_id"], pitchers["display_name"]))
default = st.session_state.get("pitcher_id")
pid = st.selectbox(f"{team} pitcher", ids, index=ids.index(default) if default in ids else 0,
                   format_func=lambda i: labels[i])
st.session_state["pitcher_id"] = pid

throws = pitchers.loc[pitchers["pitcher_id"] == pid, "throws"].iloc[0]
mine = team_ars[team_ars["pitcher_id"] == pid].sort_values("usage_pct", ascending=False)
status = roster.loc[pid, "status_label"] if pid in roster.index else "Unknown"

c1, c2, c3, c4 = st.columns(4)
c1.metric("Throws", "Right" if throws == "R" else "Left")
c2.metric("2026 pitches", f"{int(mine['pitches'].sum()):,}")
c3.metric("Pitch types", int((~mine["small_sample"]).sum()))
c4.metric("Roster status", status)

# ---------- Arsenal ----------
st.subheader("Arsenal")
tbl = pd.DataFrame({
    "Pitch": mine["pitch_name"] + mine["small_sample"].map({True: " ⚠️", False: ""}),
    "Pitches": mine["pitches"],
    "Usage %": 100 * mine["usage_pct"],
    "Velo": mine["avg_velo"],
    "Max": mine["max_velo"],
    "Spin": mine["avg_spin"],
    "Arm-side (in)": (-mine["horz_break_in"] if throws == "R" else mine["horz_break_in"]),
    "Vert (in)": mine["vert_break_in"],
    "Whiff %": 100 * mine["whiff_rate"],
    "Chase %": 100 * mine["chase_rate"],
    "CSW %": 100 * mine["csw_rate"],
    "Edge %": 100 * mine["shadow_pct"],
    "Heart %": 100 * mine["heart_pct"],
    "xwOBA contact": mine["xwoba_contact"],
})
pct = st.column_config.NumberColumn(format="%.1f")
st.dataframe(tbl, hide_index=True, width="stretch", column_config={
    "Usage %": pct, "Velo": pct, "Max": pct, "Arm-side (in)": pct, "Vert (in)": pct,
    "Whiff %": pct, "Chase %": pct, "CSW %": pct, "Edge %": pct, "Heart %": pct,
    "Spin": st.column_config.NumberColumn(format="%d"),
    "xwOBA contact": st.column_config.NumberColumn(format="%.3f"),
})
st.caption("⚠️ = fewer than 50 pitches. Edge % = pitches on the borders of the zone (command); "
           "Heart % = pitches over the middle. Movement is from the pitcher's side; vertical break is induced (gravity removed).")

st.plotly_chart(movement_chart(mine, throws), width="stretch")

# ---------- Usage by count ----------
st.subheader("What he throws by count")
side = st.radio("Batter side", ["R", "L"], horizontal=True,
                format_func=lambda s: "vs right-handed hitters" if s == "R" else "vs left-handed hitters")
u = load("pitcher_usage_by_count")
u = u[(u["pitcher_id"] == pid) & (u["batter_side"] == side)]
if u.empty:
    st.info("No pitches vs this side.")
else:
    groups = pd.concat([
        u.assign(group=u["count_group"]),
        u[u["two_strikes"]].assign(group="two strikes"),
    ])
    agg = groups.groupby(["group", "pitch_type", "pitch_name"], as_index=False)["pitches"].sum()
    totals = agg.groupby("group")["pitches"].transform("sum")
    agg["pct"] = (100 * agg["pitches"] / totals).round(1)
    order = ["first pitch", "ahead", "even", "behind", "two strikes"]
    n = agg.groupby("group")["pitches"].sum()
    agg["label"] = agg["group"].map(lambda g: f"{g} (n={int(n.get(g, 0))})")
    fig = px.bar(agg, x="pct", y="label", color="pitch_name", orientation="h",
                 color_discrete_map=name_colors(agg), text="pct",
                 category_orders={"label": [f"{g} (n={int(n.get(g, 0))})" for g in order if g in n.index]},
                 labels={"pct": "% of pitches", "label": "", "pitch_name": "Pitch"})
    fig.update_traces(texttemplate="%{text:.0f}%", textposition="inside")
    fig.update_layout(barmode="stack", height=360, margin=dict(l=10, r=10, t=10, b=10), legend_title_text="")
    st.plotly_chart(fig, width="stretch")
    st.caption("Count groups are from the pitcher's view: ahead = more strikes than balls. "
               "n = pitches in that situation; small n means less reliable percentages.")
