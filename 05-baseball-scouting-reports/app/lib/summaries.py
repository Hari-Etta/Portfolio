"""Rule-based "how to attack" summaries. Deterministic: every sentence comes from a number in the gold tables
and shows its sample size. Thresholds are simple v1 rules, listed on the Methods page."""
import pandas as pd

from lib.data import load

FASTBALLS = {"FF", "SI", "FC"}
LEAGUE_HEART = 0.256  # share of pitches in the heart zone, 2026 league (attack-zone validation)


def _pct(x: float) -> str:
    return f"{100 * x:.0f}%"


def pitcher_summary(pid: int) -> list[str]:
    """How OUR hitters should attack this pitcher."""
    out = []
    ars = load("pitcher_arsenal")
    ars = ars[ars["pitcher_id"] == pid]
    if ars.empty:
        return ["Not enough data for a summary."]

    top = ars.sort_values("usage_pct", ascending=False).iloc[0]
    out.append(f"Primary pitch: **{top['pitch_name']}** ({_pct(top['usage_pct'])} of pitches, {top['avg_velo']:.1f} mph).")
    qual = ars[ars["pitches"] >= 100]
    if len(qual) >= 2:
        w = qual.sort_values("whiff_rate", ascending=False).iloc[0]
        out.append(f"Out pitch: **{w['pitch_name']}**, {_pct(w['whiff_rate'])} whiffs per swing ({int(w['pitches'])} pitches).")
        q = qual.dropna(subset=["xwoba_contact"]).sort_values("xwoba_contact", ascending=False)
        if not q.empty and q.iloc[0]["xwoba_contact"] >= 0.400:
            h = q.iloc[0]
            out.append(f"Most hittable: **{h['pitch_name']}**, xwOBA {h['xwoba_contact']:.3f} on contact "
                       f"({int(h['pitches'])} pitches). Hunt it.")

    u = load("pitcher_usage_by_count")
    u = u[u["pitcher_id"] == pid]
    for side, label in [("R", "righties"), ("L", "lefties")]:
        us = u[u["batter_side"] == side]
        behind = us[us["count_group"] == "behind"]
        n = behind["pitches"].sum()
        if n >= 60:
            fb = behind[behind["pitch_type"].isin(FASTBALLS)]["pitches"].sum() / n
            if fb >= 0.60:
                out.append(f"Behind in the count vs {label}: **{_pct(fb)} fastballs** (n={int(n)}). Sit fastball.")
        two = us[us["two_strikes"]]
        n2 = two["pitches"].sum()
        if n2 >= 60:
            g = two.groupby("pitch_name")["pitches"].sum().sort_values(ascending=False)
            out.append(f"Two strikes vs {label}: expect the **{g.index[0]}** ({_pct(g.iloc[0] / n2)}, n={int(n2)}).")

    p = load("pitcher_platoon")
    p = p[p["pitcher_id"] == pid].set_index("batter_side")
    if {"R", "L"} <= set(p.index) and p.loc["R", "pa"] >= 100 and p.loc["L", "pa"] >= 100:
        xl, xr = p.loc["L", "xwoba"], p.loc["R", "xwoba"]
        if abs(xl - xr) >= 0.030:
            weak = "left" if xl > xr else "right"
            out.append(f"Platoon edge: hitters do better from the **{weak} side** (xwOBA {max(xl, xr):.3f} vs "
                       f"{min(xl, xr):.3f}). Stack {weak}-handed hitters.")

    tot = ars["pitches"].sum()
    heart = (ars["heart_pct"] * ars["pitches"]).sum() / tot
    if heart >= 0.29:
        out.append(f"Leaves pitches over the middle: **{_pct(heart)} in the heart** (league {_pct(LEAGUE_HEART)}). "
                   "Be aggressive early in counts.")
    elif heart <= 0.22:
        out.append(f"Lives on the edges: only {_pct(heart)} in the heart (league {_pct(LEAGUE_HEART)}). Make him come to you.")

    rg = load("pitcher_running_game")
    rg = rg[rg["pitcher_id"] == pid]
    if not rg.empty:
        r = rg.iloc[0]
        if r["steal_attempts_against"] >= 10 and r["sb_pct_against"] >= 0.85:
            out.append(f"Easy to run on: **{_pct(r['sb_pct_against'])}** steal success against him "
                       f"({int(r['steal_attempts_against'])} attempts).")

    f = load("pitcher_form")
    f = f[f["pitcher_id"] == pid]
    if not f.empty and bool(f.iloc[0]["velo_drop"]):
        out.append(f"⚠️ Fastball down {abs(f.iloc[0]['fb_velo_change']):.1f} mph lately. Check health/fatigue reports.")

    woe = load("pitcher_whiff_over_expected")
    woe = woe[(woe["pitcher_id"] == pid) & (woe["swings"] >= 150)]
    if not woe.empty:
        hi = woe.sort_values("woe_per_100", ascending=False).iloc[0]
        if hi["woe_per_100"] >= 5:
            out.append(f"Likely to cool: his **{hi['pitch_name']}** gets {hi['woe_per_100']:.0f} more whiffs per 100 swings "
                       "than the model expects, which was not repeatable in our tests.")
    return out


def hitter_summary(bid: int) -> list[str]:
    """How OUR pitchers should attack this hitter."""
    out = []
    vpt = load("hitter_vs_pitch_type")
    vpt = vpt[(vpt["batter_id"] == bid) & (vpt["pitches_seen"] >= 50) & (vpt["pa_ended"] >= 15)]
    for hand, label in [("R", "RHP"), ("L", "LHP")]:
        v = vpt[vpt["pitcher_hand"] == hand].dropna(subset=["xwoba"])
        if len(v) >= 2:
            weak = v.sort_values("xwoba").iloc[0]
            strong = v.sort_values("xwoba", ascending=False).iloc[0]
            out.append(f"vs {label}: attack with the **{weak['pitch_name']}** (xwOBA {weak['xwoba']:.3f}, "
                       f"K {_pct(weak['k_pct'])}, {int(weak['pa_ended'])} PA); avoid the **{strong['pitch_name']}** "
                       f"(xwOBA {strong['xwoba']:.3f}, {int(strong['pa_ended'])} PA).")

    sd = load("hitter_swing_decisions")
    c = sd[(sd["batter_id"] == bid) & (sd["attack_zone"] == "chase")]
    if not c.empty and c.iloc[0]["pitches"] >= 100:
        d = c.iloc[0]["swing_rate_vs_league"]
        if d >= 0.03:
            out.append(f"Chases: swings at **{_pct(c.iloc[0]['swing_rate'])}** of chase pitches ({100 * d:+.0f} pts vs league). "
                       "Expand the zone, especially with two strikes.")
        elif d <= -0.03:
            out.append(f"Disciplined: chases {100 * abs(d):.0f} pts less than the league. Don't nibble; win the edges early.")

    bt = load("hitter_bat_tracking")
    bt = bt[bt["batter_id"] == bid].set_index("pitch_group")
    if {"fastball", "breaking"} <= set(bt.index) and bt.loc["breaking", "competitive_swings"] >= 50:
        diff = bt.loc["breaking", "avg_swing_length"] - bt.loc["fastball", "avg_swing_length"]
        if diff >= 0.6:
            out.append(f"Swing lengthens by {diff:.1f} ft vs breaking balls. Finish him with spin.")

    spr = load("hitter_spray")
    s = spr[spr["batter_id"] == bid]
    n = s["batted_balls"].sum()
    if n >= 100:
        pull = s[s["pull_side"] == "pull"]["batted_balls"].sum() / n
        opp = s[s["pull_side"] == "opposite"]["batted_balls"].sum() / n
        if pull >= 0.50:
            out.append(f"Pull-heavy: **{_pct(pull)}** of balls in play pulled ({int(n)} balls). Shade the defense to his pull side.")
        elif opp >= 0.33:
            out.append(f"Uses the whole field: {_pct(opp)} to the opposite field ({int(n)} balls). Play him straight up.")

    sp = load("hitter_splits")
    sp = sp[sp["batter_id"] == bid].set_index("pitcher_hand")
    if {"R", "L"} <= set(sp.index) and sp.loc["L", "pa"] >= 80 and sp.loc["R", "pa"] >= 80:
        d = sp.loc["R", "xwoba"] - sp.loc["L", "xwoba"]
        if abs(d) >= 0.040:
            weaker = "LHP" if d > 0 else "RHP"
            out.append(f"Platoon split: noticeably weaker vs **{weaker}** (xwOBA gap {abs(d):.3f}). Consider a matchup reliever.")

    rr = load("runner_running_game")
    r = rr[rr["runner_id"] == bid]
    if not r.empty and r.iloc[0]["opps_2b"] >= 20:
        lg = rr["att_2b"].sum() / rr["opps_2b"].sum()
        if r.iloc[0]["attempt_rate_2b"] >= 2 * lg:
            out.append(f"Will run: attempts a steal in **{_pct(r.iloc[0]['attempt_rate_2b'])}** of chances "
                       f"(league {_pct(lg)}), {_pct(r.iloc[0]['sb_pct'])} success. Vary looks, be quick to the plate.")

    f = load("hitter_form")
    f = f[f["batter_id"] == bid]
    if not f.empty and f.iloc[0]["form"] in ("hot", "cold"):
        out.append(f"Recently {f.iloc[0]['form']} (xwOBA {f.iloc[0]['xwoba_change']:+.3f} over {int(f.iloc[0]['l30_pa'])} PA). "
                   "About half of a streak tends to persist.")
    return out or ["No strong tendencies at current sample sizes."]
