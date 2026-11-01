"""Hitter report, part 1: picker, header, splits, vs pitch types, zone map, swing decisions."""
import pandas as pd
import plotly.express as px
import streamlit as st

from lib.charts import zone_heatmap
from lib.data import load

f1 = st.column_config.NumberColumn(format="%.1f")
f3 = st.column_config.NumberColumn(format="%.3f")

st.title("🏏 Hitter report")
team = st.session_state.get("team")
if team is None:
    st.info("Pick an opponent team on the Home page first.")
    st.page_link("pages/home.py", label="Go to Home", icon="🏠")
    st.stop()

players = load("players")
roster = load("current_roster").set_index("player_id")
splits_all = load("hitter_splits")

team_splits = splits_all[splits_all["last_team"] == team]
hitters = (team_splits.groupby("batter_id", as_index=False)["pa"].sum()
           .merge(players[["player_id", "display_name", "bats"]], left_on="batter_id", right_on="player_id")
           .sort_values("pa", ascending=False))
ids = hitters["batter_id"].tolist()
labels = dict(zip(hitters["batter_id"], hitters["display_name"]))
default = st.session_state.get("batter_id")
bid = st.selectbox(f"{team} hitter", ids, index=ids.index(default) if default in ids else 0,
                   format_func=lambda i: labels[i])
st.session_state["batter_id"] = bid

bats = hitters.loc[hitters["batter_id"] == bid, "bats"].iloc[0]
mine = team_splits[team_splits["batter_id"] == bid]
pa = int(mine["pa"].sum())
woba = (mine["woba"] * mine["pa"]).sum() / pa if pa else float("nan")
xwoba = (mine["xwoba"] * mine["pa"]).sum() / pa if pa else float("nan")
status = roster.loc[bid, "status_label"] if bid in roster.index else "Unknown"

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Bats", {"R": "Right", "L": "Left", "S": "Switch"}.get(bats, bats))
c2.metric("2026 PA", f"{pa:,}")
c3.metric("wOBA", f"{woba:.3f}")
c4.metric("xwOBA", f"{xwoba:.3f}")
c5.metric("Roster status", status)

# ---------- Splits ----------
st.subheader("vs right- and left-handed pitchers")
sp = mine.set_index("pitcher_hand").reindex(["R", "L"])
st.dataframe(pd.DataFrame({
    "vs": ["Right-handed pitchers", "Left-handed pitchers"],
    "PA": sp["pa"].values,
    "K %": (100 * sp["k_pct"]).values,
    "BB %": (100 * sp["bb_pct"]).values,
    "HBP %": (100 * sp["hbp_pct"]).values,
    "wOBA": sp["woba"].values,
    "xwOBA": sp["xwoba"].values,
    "Whiff %": (100 * sp["whiff_rate"]).values,
    "Chase %": (100 * sp["chase_rate"]).values,
    "Hard-hit %": (100 * sp["hard_hit_pct"]).values,
}), hide_index=True, width="stretch", column_config={
    "K %": f1, "BB %": f1, "HBP %": f1, "Whiff %": f1, "Chase %": f1, "Hard-hit %": f1, "wOBA": f3, "xwOBA": f3})
st.caption("wOBA counts reached-on-error as an out; xwOBA judges contact quality (less luck). Higher is better for the hitter.")

# ---------- vs pitch types ----------
st.subheader("vs each pitch type")
hand = st.radio("Pitcher hand", ["R", "L"], horizontal=True,
                format_func=lambda h: "vs RHP" if h == "R" else "vs LHP")
vpt = load("hitter_vs_pitch_type")
vpt = vpt[(vpt["batter_id"] == bid) & (vpt["pitcher_hand"] == hand)].sort_values("pitches_seen", ascending=False)
if vpt.empty:
    st.info("No pitches seen from this side.")
else:
    st.dataframe(pd.DataFrame({
        "Pitch": vpt["pitch_name"] + vpt["small_sample"].map({True: " ⚠️", False: ""}),
        "Seen": vpt["pitches_seen"],
        "Swing %": 100 * vpt["swing_rate"],
        "Whiff %": 100 * vpt["whiff_rate"],
        "Chase %": 100 * vpt["chase_rate"],
        "PA ended": vpt["pa_ended"],
        "K %": 100 * vpt["k_pct"],
        "wOBA": vpt["woba"],
        "xwOBA": vpt["xwoba"],
        "Hard-hit %": 100 * vpt["hard_hit_pct"],
    }), hide_index=True, width="stretch", column_config={
        "Swing %": f1, "Whiff %": f1, "Chase %": f1, "K %": f1, "Hard-hit %": f1, "wOBA": f3, "xwOBA": f3})
    st.caption("⚠️ = fewer than 50 pitches seen. wOBA/xwOBA/K% use plate appearances that ENDED on that pitch type.")

# ---------- Zone map ----------
st.subheader("Zone map (catcher's view)")
z1, z2 = st.columns(2)
zhand = z1.radio("Pitcher hand ", ["R", "L"], horizontal=True,
                 format_func=lambda h: "vs RHP" if h == "R" else "vs LHP")
zmetric = z2.selectbox("Color by", ["How pitchers attack him", "Swing %", "Whiff % on swings", "xwOBA on contact"])
hz = load("hitter_zones")
hz = hz[(hz["batter_id"] == bid) & (hz["pitcher_hand"] == zhand)].copy()
if hz.empty:
    st.info("No pitches seen from this side.")
else:
    hz["seen"] = 100 * hz["seen_pct"]
    hz["swing"] = 100 * hz["swing_rate"]
    hz["whiff"] = 100 * hz["whiff_rate"]
    hz["xw"] = hz["xwoba_contact"].where(hz["batted_balls"] >= 5)
    if zmetric == "How pitchers attack him":
        fig = zone_heatmap(hz, "seen", "{:.0f}%", colorscale="Greys")
    elif zmetric == "Swing %":
        fig = zone_heatmap(hz, "swing", "{:.0f}%", colorscale="Oranges")
    elif zmetric == "Whiff % on swings":
        fig = zone_heatmap(hz, "whiff", "{:.0f}%", colorscale="Blues")
    else:
        fig = zone_heatmap(hz, "xw", "{:.3f}", colorscale="RdYlGn")
    st.plotly_chart(fig, width="stretch")
    st.caption(f"Based on {int(hz['pitches_seen'].sum()):,} pitches seen. xwOBA shows '-' where fewer than 5 balls "
               "were put in play. For a right-handed hitter, inside is the catcher's left.")

# ---------- Swing decisions ----------
st.subheader("Swing decisions")
sd = load("hitter_swing_decisions")
order = ["heart", "shadow", "chase", "waste"]
sd = sd[sd["batter_id"] == bid].set_index("attack_zone").reindex(order).reset_index()
if sd["pitches"].isna().all():
    st.info("No swing-decision data.")
else:
    chart = pd.concat([
        pd.DataFrame({"zone": sd["attack_zone"], "who": "him", "swing %": 100 * sd["swing_rate"]}),
        pd.DataFrame({"zone": sd["attack_zone"], "who": "league", "swing %": 100 * sd["league_swing_rate"]}),
    ])
    fig = px.bar(chart, x="zone", y="swing %", color="who", barmode="group", text="swing %",
                 category_orders={"zone": order}, color_discrete_map={"him": "#e4572e", "league": "#8a8a8a"},
                 labels={"zone": "attack zone", "who": ""})
    fig.update_traces(texttemplate="%{text:.0f}%", textposition="outside")
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, width="stretch")
    st.dataframe(pd.DataFrame({
        "Zone": sd["attack_zone"], "Pitches": sd["pitches"],
        "Swing %": 100 * sd["swing_rate"], "vs league (pts)": 100 * sd["swing_rate_vs_league"],
        "Whiff %": 100 * sd["whiff_rate"], "Runs per 100": sd["runs_per_100"],
    }), hide_index=True, width="stretch", column_config={
        "Swing %": f1, "vs league (pts)": f1, "Whiff %": f1, "Runs per 100": st.column_config.NumberColumn(format="%.2f")})
    st.caption("Heart = middle of the zone, shadow = edges, chase = just off the plate, waste = far off. "
               "Swinging more than the league at chase/waste pitches is a weakness to exploit. "
               "Runs per 100 includes contact results, not decisions alone.")
