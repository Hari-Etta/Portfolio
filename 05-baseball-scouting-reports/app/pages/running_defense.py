"""Running game & defense for the selected opponent: runners, pitchers' hold, catchers, fielders."""
import pandas as pd
import plotly.express as px
import streamlit as st

from lib.data import load
from lib.status import add_status, snapshot_caption

f1 = st.column_config.NumberColumn(format="%.1f")
f2 = st.column_config.NumberColumn(format="%.2f")
f3 = st.column_config.NumberColumn(format="%.3f")

st.title("🏃 Running game & defense")
team = st.session_state.get("team")
if team is None:
    st.info("Pick an opponent team on the Home page first.")
    st.page_link("pages/home.py", label="Go to Home", icon="🏠")
    st.stop()
st.caption(f"{team} · {snapshot_caption()}")

runners_tab, pitchers_tab, catchers_tab, fielders_tab = st.tabs(["Runners", "Pitchers", "Catchers", "Fielders"])

# ---------- Runners ----------
with runners_tab:
    rr = load("runner_running_game")
    lg_rate = rr["att_2b"].sum() / rr["opps_2b"].sum()
    lg_sb = rr["sb"].sum() / rr["attempts"].sum()
    mine = add_status(rr[(rr["last_team"] == team) & (rr["opps_2b"] > 0)], "runner_id", team)
    mine = mine.sort_values("attempts", ascending=False)
    c1, c2 = st.columns(2)
    c1.metric("League attempt rate (steal of 2nd per opportunity)", f"{100 * lg_rate:.1f}%")
    c2.metric("League steal success", f"{100 * lg_sb:.1f}%")
    st.dataframe(pd.DataFrame({
        "Runner": mine["runner_name"] + mine["small_sample"].map({True: " ⚠️", False: ""}),
        "Status": mine["Status"],
        "Opportunities": mine["opps_2b"],
        "Attempt rate %": 100 * mine["attempt_rate_2b"],
        "Attempts": mine["attempts"], "SB": mine["sb"], "CS": mine["cs"],
        "SB %": 100 * mine["sb_pct"],
        "Steals of 3rd": mine["sb_3b"],
        "Picked off": mine["picked_off"],
        "Sprint speed (ft/s)": mine["sprint_speed"],
        "Home to 1st (s)": mine["hp_to_1b"],
    }), hide_index=True, width="stretch", column_config={
        "Attempt rate %": f1, "SB %": f1, "Sprint speed (ft/s)": f1, "Home to 1st (s)": f2})
    st.caption("Opportunity = on first base with second base open. ⚠️ = fewer than 20 opportunities. "
               "SB % counts pickoff-caught-stealing as caught stealing.")

    chart = rr[(rr["opps_2b"] >= 30) & rr["sprint_speed"].notna()].copy()
    chart["team"] = chart["last_team"].eq(team).map({True: team, False: "rest of MLB"})
    chart["attempt rate %"] = 100 * chart["attempt_rate_2b"]
    fig = px.scatter(chart, x="sprint_speed", y="attempt rate %", color="team", hover_name="runner_name",
                     color_discrete_map={team: "#e4572e", "rest of MLB": "#7f7f7f"}, opacity=0.8,
                     labels={"sprint_speed": "sprint speed (ft/s)"})
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10), legend_title_text="")
    st.plotly_chart(fig, width="stretch")
    st.caption("Runners with 30+ opportunities. Faster runners attempt more (correlation +0.62) but don't succeed more "
               "(+0.06): slower runners tend to go only when they're sure.")

# ---------- Pitchers ----------
with pitchers_tab:
    pr = load("pitcher_running_game")
    lg_throws = pr["pickoff_throws_1b"].sum() / pr["opps_1b"].sum()
    lg_sb_against = pr["sb_allowed"].sum() / pr["steal_attempts_against"].sum()
    mine = add_status(pr[pr["last_team"] == team], "pitcher_id", team).sort_values("opps_1b", ascending=False)
    c1, c2 = st.columns(2)
    c1.metric("League pickoff throws to 1st per opportunity", f"{lg_throws:.2f}")
    c2.metric("League steal success against pitchers", f"{100 * lg_sb_against:.1f}%")
    st.dataframe(pd.DataFrame({
        "Pitcher": mine["pitcher_name"] + mine["small_sample"].map({True: " ⚠️", False: ""}),
        "Status": mine["Status"],
        "Throws": mine["throws"],
        "Opportunities": mine["opps_1b"],
        "Pickoff throws per opp": mine["throws_per_opp"],
        "Pickoffs": mine["pickoffs"],
        "Pickoff errors": mine["pickoff_errors"],
        "Steal attempts against": mine["steal_attempts_against"],
        "SB allowed": mine["sb_allowed"], "CS": mine["cs"],
        "SB % against": 100 * mine["sb_pct_against"],
    }), hide_index=True, width="stretch", column_config={"Pickoff throws per opp": f2, "SB % against": f1})
    st.caption("Opportunity = runner on first with second open. ⚠️ = fewer than 30 opportunities. "
               "Under pitch-clock rules, pitchers get two free disengagements per plate appearance; "
               "step-offs without a throw aren't in the public feed, so only throws are counted.")

# ---------- Catchers ----------
with catchers_tab:
    cd = load("catcher_defense")
    lg_cs = cd["cs"].sum() / cd["steal_attempts"].sum()
    mine = add_status(cd[cd["last_team"] == team], "catcher_id", team).sort_values("steal_attempts", ascending=False)
    st.metric("League caught-stealing rate (catchers)", f"{100 * lg_cs:.1f}%")
    st.dataframe(pd.DataFrame({
        "Catcher": mine["catcher_name"] + mine["small_sample"].map({True: " ⚠️", False: ""}),
        "Status": mine["Status"],
        "Steal attempts": mine["steal_attempts"],
        "CS": mine["cs"], "SB allowed": mine["sb_allowed"],
        "CS %": 100 * mine["cs_rate"],
        "Pop time to 2nd (s)": mine["pop_time_2b"],
        "Exchange (s)": mine["exchange_time"],
        "Arm (mph)": mine["arm_strength"],
    }), hide_index=True, width="stretch", column_config={
        "CS %": f1, "Pop time to 2nd (s)": f2, "Exchange (s)": f2, "Arm (mph)": f1})
    st.caption("Catcher CS excludes pickoff-caught-stealing (those start with the pitcher's throw). "
               "⚠️ = fewer than 20 attempts. Pop time, exchange and arm strength from Baseball Savant.")
    chart = cd[(cd["steal_attempts"] >= 20) & cd["pop_time_2b"].notna()].copy()
    chart["team"] = chart["last_team"].eq(team).map({True: team, False: "rest of MLB"})
    chart["CS %"] = 100 * chart["cs_rate"]
    fig = px.scatter(chart, x="pop_time_2b", y="CS %", color="team", hover_name="catcher_name",
                     color_discrete_map={team: "#e4572e", "rest of MLB": "#7f7f7f"},
                     labels={"pop_time_2b": "pop time to 2nd (s), faster = left"})
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10), legend_title_text="")
    st.plotly_chart(fig, width="stretch")
    st.caption("Catchers with 20+ attempts. Quicker pop times go with more runners caught (correlation -0.58).")

# ---------- Fielders ----------
with fielders_tab:
    fd = load("fielder_defense")
    mine = add_status(fd[fd["last_team"] == team], "player_id", team).sort_values("oaa", ascending=False)
    if mine.empty:
        st.info("No qualified fielders for this team.")
    else:
        st.dataframe(pd.DataFrame({
            "Fielder": mine["player_name"], "Status": mine["Status"], "Position": mine["position"],
            "OAA": mine["oaa"], "Runs prevented": mine["fielding_runs_prevented"],
            "OAA vs RHH": mine["oaa_vs_rhh"], "OAA vs LHH": mine["oaa_vs_lhh"],
            "Catch % (5-star, hardest)": mine["catch_pct_5star"],
            "Jump vs avg (ft)": mine["jump_ft"],
        }), hide_index=True, width="stretch", column_config={"Jump vs avg (ft)": f1})
        st.caption("OAA = Outs Above Average (0 = average). Catch probability and jump apply to outfielders.")

        pick = st.selectbox("Directional breakdown", mine["player_id"].tolist(),
                            format_func=lambda i: mine.set_index("player_id").loc[i, "player_name"])
        r = mine.set_index("player_id").loc[pick]
        dirs = pd.DataFrame({
            "direction": ["in front (charging)", "toward 3B line", "toward 1B line", "behind (going back)"],
            "OAA": [r["oaa_in_front"], r["oaa_toward_3b_line"], r["oaa_toward_1b_line"], r["oaa_behind"]],
        })
        fig = px.bar(dirs, x="direction", y="OAA", text="OAA",
                     color=dirs["OAA"].ge(0).map({True: "above average", False: "below average"}),
                     color_discrete_map={"above average": "#2ca02c", "below average": "#d62728"})
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10), legend_title_text="", xaxis_title="")
        st.plotly_chart(fig, width="stretch")
        if pd.notna(r["reaction_vs_avg_ft"]):
            j1, j2 = st.columns(2)
            j1.metric("Reaction vs average", f"{r['reaction_vs_avg_ft']:+.1f} ft")
            j2.metric("Burst vs average", f"{r['burst_vs_avg_ft']:+.1f} ft")
        st.caption("Directional parts add up to total OAA (up to rounding). "
                   "Route efficiency is not shown yet: its sign convention is being checked (see BACKLOG.md).")
