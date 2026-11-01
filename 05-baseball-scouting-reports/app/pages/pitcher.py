"""Pitcher report, part 1: picker, header, arsenal, movement, usage by count."""
import pandas as pd
import plotly.express as px
import streamlit as st

from lib.charts import field_chart, movement_chart, name_colors, zone_heatmap
from lib.data import load, woba_col, woba_note

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

from lib.summaries import pitcher_summary

with st.container(border=True):
    st.markdown("#### 📝 How to attack him")
    for line in pitcher_summary(pid):
        st.markdown(f"- {line}")
    st.caption("Rule-based from the tables below; every claim shows its sample size. Thresholds are on the Methods page.")

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


# ---------- Location ----------
st.subheader("Where he throws it (catcher's view)")
loc = load("pitcher_locations")
loc = loc[loc["pitcher_id"] == pid]
lc1, lc2, lc3 = st.columns(3)
pitch_opts = ["All pitches"] + mine["pitch_name"].tolist()
loc_pitch = lc1.selectbox("Pitch", pitch_opts)
loc_side = lc2.radio("Batter side ", ["R", "L"], horizontal=True,
                     format_func=lambda s: "vs RHH" if s == "R" else "vs LHH")
metric = lc3.selectbox("Color by", ["Where he throws it", "Whiff % on swings", "xwOBA on contact"])
cells = loc[loc["batter_side"] == loc_side]
if loc_pitch != "All pitches":
    cells = cells[cells["pitch_name"] == loc_pitch]
if cells.empty:
    st.info("No pitches for this selection.")
else:
    cells = cells.assign(swings=cells["swing_rate"] * cells["pitches"])
    cells = cells.assign(whiffs=cells["whiff_rate"].fillna(0) * cells["swings"],
                         xw=cells["xwoba_contact"] * cells["pitches"])
    z = cells.groupby("zone", as_index=False)[["pitches", "swings", "whiffs", "xw"]].sum()
    z["share"] = 100 * z["pitches"] / z["pitches"].sum()
    z["whiff"] = 100 * z["whiffs"] / z["swings"].where(z["swings"] > 0)
    z["xwoba"] = z["xw"] / z["pitches"]
    if metric == "Where he throws it":
        fig = zone_heatmap(z, "share", "{:.0f}%")
    elif metric == "Whiff % on swings":
        fig = zone_heatmap(z, "whiff", "{:.0f}%", colorscale="Blues")
    else:
        fig = zone_heatmap(z, "xwoba", "{:.3f}", colorscale="RdYlGn_r")
    st.plotly_chart(fig, width="stretch")
    st.caption(f"Based on {int(z['pitches'].sum()):,} pitches. Zones are adjusted to each batter's height. "
               "For a right-handed hitter, inside is the catcher's left.")

# ---------- Platoon, form, home/road ----------
st.subheader("Results vs left- and right-handed hitters")
plat = load("pitcher_platoon")
plat = plat[plat["pitcher_id"] == pid].set_index("batter_side").reindex(["R", "L"])
plat_tbl = pd.DataFrame({
    "vs": ["Right-handed hitters", "Left-handed hitters"],
    "PA": plat["pa"].values,
    "K %": (100 * plat["k_pct"]).values,
    "BB %": (100 * plat["bb_pct"]).values,
    "wOBA": plat[woba_col()].values,
    "xwOBA": plat["xwoba"].values,
    "Whiff %": (100 * plat["whiff_rate"]).values,
    "Chase %": (100 * plat["chase_rate"]).values,
    "Hard-hit %": (100 * plat["hard_hit_pct"]).values,
})
f1, f3 = st.column_config.NumberColumn(format="%.1f"), st.column_config.NumberColumn(format="%.3f")
st.dataframe(plat_tbl, hide_index=True, width="stretch", column_config={
    "K %": f1, "BB %": f1, "Whiff %": f1, "Chase %": f1, "Hard-hit %": f1, "wOBA": f3, "xwOBA": f3})
st.caption(f"{woba_note()} xwOBA judges contact quality (less luck). Lower is better for the pitcher.")

fc, hc = st.columns(2)
with fc:
    st.subheader("Recent form")
    form = load("pitcher_form")
    frow = form[form["pitcher_id"] == pid]
    if frow.empty:
        st.info("No form data.")
    else:
        fr = frow.iloc[0]
        st.metric("Form (last 30 days vs earlier)", str(fr["form"]).title())
        m1, m2 = st.columns(2)
        if pd.notna(fr["l30_xwoba_allowed"]):
            m1.metric("xwOBA allowed, last 30", f"{fr['l30_xwoba_allowed']:.3f}",
                      delta=f"{fr['xwoba_change']:+.3f}" if pd.notna(fr["xwoba_change"]) else None, delta_color="inverse")
        if pd.notna(fr["l30_fb_velo"]):
            m2.metric(f"{fr['fb_type']} velo, last 30", f"{fr['l30_fb_velo']:.1f} mph",
                      delta=f"{fr['fb_velo_change']:+.1f} mph" if pd.notna(fr["fb_velo_change"]) else None)
        if fr["velo_drop"]:
            st.warning("Fastball velocity is down 1+ mph from earlier in the season: worth a closer look (fatigue or injury?).")
        st.caption(f"Window ends {pd.to_datetime(fr['as_of_date']):%b %d, %Y}. "
                   "Backtest: about half of a 30-day streak tends to carry forward.")
with hc:
    st.subheader("Home vs road")
    hr = load("player_home_road")
    hr = hr[(hr["role"] == "pitcher") & (hr["player_id"] == pid)].set_index("venue").reindex(["home", "road"])
    st.dataframe(pd.DataFrame({
        "Venue": ["Home", "Road"], "PA": hr["pa"].values,
        "wOBA": hr[woba_col()].values, "xwOBA": hr["xwoba"].values, "K %": (100 * hr["k_pct"]).values,
    }), hide_index=True, width="stretch", column_config={"wOBA": f3, "xwOBA": f3, "K %": f1})
    st.caption("Shows park effects (e.g. Coors Field); not park-adjusted.")

# ---------- Spray allowed ----------
st.subheader("Where hitters hit it against him (for positioning)")
spray = load("pitcher_spray_allowed")
spray = spray[spray["pitcher_id"] == pid]
s1, s2 = st.columns(2)
sp_side = s1.radio("Batter side  ", ["R", "L"], horizontal=True,
                   format_func=lambda s: "vs RHH" if s == "R" else "vs LHH")
sp_group = s2.selectbox("Pitch group", ["All", "fastball", "breaking", "offspeed"])
sel = spray[spray["batter_side"] == sp_side]
if sp_group != "All":
    sel = sel[sel["pitch_group"] == sp_group]
if sel.empty:
    st.info("No batted balls for this selection.")
else:
    zones = sel.groupby(["field_zone", "depth", "direction"], as_index=False)["batted_balls"].sum()
    zones["share"] = zones["batted_balls"] / zones["batted_balls"].sum()
    st.plotly_chart(field_chart(zones), width="stretch")
    top = zones.sort_values("share", ascending=False).iloc[0]
    st.caption(f"{int(zones['batted_balls'].sum())} batted balls. Most common: "
               f"{top['depth'].replace('_', ' ')} {top['direction']} ({100 * top['share']:.0f}%). "
               "Location = where the ball was fielded. Left field is on the left.")


