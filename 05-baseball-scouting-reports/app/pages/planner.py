"""Pitch planner: score one of our pitcher's pitches against the opposing hitter across a grid of locations."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib.data import load
from lib.model import FASTBALLS, GROUPS, attack_zone, load_model, predict

st.title("🧠 Pitch planner")
st.caption("Uses the calibrated whiff model (Phase 3). Pick our pitcher and pitch, their hitter, and the count.")
team = st.session_state.get("team")
if team is None:
    st.info("Pick an opponent team on the Home page first.")
    st.page_link("pages/home.py", label="Go to Home", icon="🏠")
    st.stop()

players = load("players")
ars = load("pitcher_arsenal")
vpt = load("hitter_vs_pitch_type")
sd = load("hitter_swing_decisions")
names = dict(zip(players["player_id"], players["display_name"]))
bats = dict(zip(players["player_id"], players["bats"]))

# ---------- Selections ----------
hs = load("hitter_splits")
team_hitters = (hs[hs["last_team"] == team].groupby("batter_id")["pa"].sum().sort_values(ascending=False).index.tolist())
c1, c2 = st.columns(2)
default_b = st.session_state.get("batter_id")
bid = c1.selectbox(f"Their hitter ({team})", team_hitters,
                   index=team_hitters.index(default_b) if default_b in team_hitters else 0,
                   format_func=lambda i: names.get(i, i))
teams = sorted(ars["last_team"].dropna().unique())
our_team = c2.selectbox("Our pitcher's team", teams, index=teams.index(st.session_state.get("our_team", teams[0]))
                        if st.session_state.get("our_team") in teams else 0)
st.session_state["our_team"] = our_team

pool = ars[ars["last_team"] == our_team]
pitchers = pool.groupby("pitcher_id")["pitches"].sum().sort_values(ascending=False).index.tolist()
c3, c4, c5, c6 = st.columns(4)
pid = c3.selectbox("Our pitcher", pitchers, format_func=lambda i: names.get(i, i))
mine = pool[(pool["pitcher_id"] == pid) & (pool["pitches"] >= 50)].sort_values("usage_pct", ascending=False)
pitch = c4.selectbox("Pitch", mine["pitch_type"].tolist(),
                     format_func=lambda t: mine.set_index("pitch_type").loc[t, "pitch_name"])
balls = c5.selectbox("Balls", [0, 1, 2, 3])
strikes = c6.selectbox("Strikes", [0, 1, 2], index=2)
view = st.radio("Show", ["Whiff per pitch (× his swing rate)", "Whiff if he swings"], horizontal=True)

# ---------- Build the pitch from the pitcher's real averages ----------
p = mine.set_index("pitch_type").loc[pitch]
throws = p["throws"]
arm_side = -p["horz_break_in"] if throws == "R" else p["horz_break_in"]
fb = mine[mine["pitch_type"].isin(FASTBALLS)]
if fb.empty:
    fb = pool[(pool["pitcher_id"] == pid) & pool["pitch_type"].isin(FASTBALLS)]
w = fb["pitches"]
fb_velo = (fb["avg_velo"] * w).sum() / w.sum() if len(fb) else np.nan
fb_ivb = (fb["vert_break_in"] * w).sum() / w.sum() if len(fb) else np.nan
fb_arm = ((-fb["horz_break_in"] if throws == "R" else fb["horz_break_in"]) * w).sum() / w.sum() if len(fb) else np.nan

b = bats.get(bid, "R")
stand = ("L" if throws == "R" else "R") if b == "S" else b

# Tendencies from the full 2026 season (what you'd know before a future game).
hv = vpt[vpt["batter_id"] == bid].copy()
hv["swings"] = hv["swing_rate"] * hv["pitches_seen"]
hv["whiffs"] = hv["whiff_rate"].fillna(0) * hv["swings"]
group = GROUPS.get(pitch, "other")
hg = hv[hv["pitch_type"].map(GROUPS).fillna("other") == group]
pa = pool[pool["pitcher_id"] == pid].copy()
pa["swings"] = 0.48 * pa["pitches"]  # approx: league swing rate ~48% (only a sample-size signal for the model)
pt = pa[pa["pitch_type"] == pitch]

x = np.linspace(-2.2, 2.2, 11)    # ft, + = away from the hitter (wide enough to reach "waste" distance)
z = np.linspace(-1.0, 2.0, 11)    # fraction of his zone: 0 = bottom, 1 = top
X, Z = np.meshgrid(x, z)
ratio, zone = attack_zone(X.ravel(), Z.ravel())
rows = pd.DataFrame({
    "pitch_type": pitch, "pitch_group": group, "attack_zone": zone,
    "p_throws": throws, "stand": stand, "same_side": float(throws == stand),
    "release_speed": p["avg_velo"], "spin_rate": p["avg_spin"], "arm_angle": p["arm_angle"],
    "ivb_in": p["vert_break_in"], "arm_side_break_in": arm_side,
    "plate_x_away": X.ravel(), "plate_z_norm": Z.ravel(), "zone_ratio": ratio,
    "velo_diff_fb": p["avg_velo"] - fb_velo, "ivb_diff_fb": p["vert_break_in"] - fb_ivb, "hb_diff_fb": arm_side - fb_arm,
    "balls": balls, "strikes": strikes,
    "bat_prior_swings": hv["swings"].sum(), "bat_prior_whiff_rate": hv["whiffs"].sum() / max(hv["swings"].sum(), 1),
    "bat_grp_prior_swings": hg["swings"].sum(), "bat_grp_prior_whiff_rate": hg["whiffs"].sum() / max(hg["swings"].sum(), 1),
    "pit_prior_swings": pa["swings"].sum(), "pit_prior_whiff_rate": (pa["whiff_rate"] * pa["swings"]).sum() / max(pa["swings"].sum(), 1),
    "pit_type_prior_swings": pt["swings"].sum(), "pit_type_prior_whiff_rate": float(pt["whiff_rate"].iloc[0]) if len(pt) else np.nan,
})

booster, meta = load_model()
p_whiff = predict(booster, meta, rows)
# Swing chance fades smoothly with distance: the league's swing rate by attack zone (interpolated on zone_ratio),
# scaled by this hitter's own swing tendency in each band. An approximation until a real swing model exists.
order = ["heart", "shadow", "chase", "waste"]
centers = {"heart": 0.33, "shadow": 1.0, "chase": 1.67, "waste": 2.5}
league_sd = sd.groupby("attack_zone")["league_swing_rate"].first()
his_sd = sd[sd["batter_id"] == bid].set_index("attack_zone")["swing_rate"]
league_curve = np.interp(ratio, [centers[k] for k in order], [league_sd[k] for k in order])
factor = pd.Series(zone).map(lambda k: his_sd.get(k, league_sd[k]) / league_sd[k] if league_sd[k] > 0 else 1.0).to_numpy()
p_swing = league_curve * factor
values = p_whiff * p_swing if view.startswith("Whiff per pitch") else p_whiff
grid = (100 * values).reshape(Z.shape)

# ---------- Heatmap ----------
fig = go.Figure(go.Heatmap(x=x, y=z, z=grid, colorscale="Blues", zmin=0,
                           text=np.round(grid).astype(int), texttemplate="%{text}%",
                           hovertemplate="away %{x:.1f} ft · height %{y:.2f} of zone<br>%{z:.1f}%<extra></extra>",
                           colorbar=dict(title="%")))
fig.add_shape(type="rect", x0=-0.83, x1=0.83, y0=0, y1=1, line=dict(color="white", width=3))
best = int(np.nanargmax(values))
fig.add_trace(go.Scatter(x=[X.ravel()[best]], y=[Z.ravel()[best]], mode="markers",
                         marker=dict(symbol="star", size=22, color="#e4572e", line=dict(color="white", width=1)),
                         name="best spot", hoverinfo="skip"))
fig.update_layout(height=520, margin=dict(l=10, r=10, t=30, b=10), showlegend=False,
                  xaxis_title="← inside      horizontal location (ft, hitter's view)      away →",
                  yaxis_title="height (0 = bottom of his zone, 1 = top)")
st.plotly_chart(fig, width="stretch")

bx, bz = X.ravel()[best], Z.ravel()[best]
where = ("away" if bx > 0.4 else "inside" if bx < -0.4 else "middle") + ", " + \
        ("below the zone" if bz < 0 else "low" if bz < 0.34 else "up" if bz > 0.66 else "belt-high" if bz <= 1 else "above the zone")
st.success(f"**{mine.set_index('pitch_type').loc[pitch, 'pitch_name']}** from {names.get(pid)} to {names.get(bid)} at "
           f"{balls}-{strikes}: best spot is **{where}** ({100 * values[best]:.0f}% "
           f"{'whiff per pitch' if view.startswith('Whiff per pitch') else 'whiff if he swings'}).")
st.caption("White box = strike zone (typical 1.8 ft height). 'Whiff if he swings' is the model's calibrated probability; "
           "'per pitch' multiplies by an estimated swing chance that fades with distance from the zone (league curve scaled by this hitter's tendencies): an approximation until a dedicated swing model exists. "
           "Pitch shape = this pitcher's 2026 averages for the pitch. Pitcher swing counts are approximated from pitch counts.")

