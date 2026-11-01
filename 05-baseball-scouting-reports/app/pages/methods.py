"""Methods & data: sources, freshness, definitions, summary thresholds, validations, limitations."""
import pandas as pd
import streamlit as st

from lib.data import backend, load

st.title("📘 Methods & data")

roster = load("current_roster")
tx = load("transactions")
c1, c2, c3 = st.columns(3)
c1.metric("Season covered", "2026 regular season")
c2.metric("Roster snapshot", f"{pd.to_datetime(roster['snapshot_date'].max()):%b %d, %Y}")
c3.metric("Latest transaction", f"{pd.to_datetime(tx['transaction_date']).max():%b %d, %Y}")
st.caption(f"Data backend: {backend()} (read-only access to finished tables). Rosters and transactions refresh daily.")

st.markdown("""
### Sources and pipeline
- **Statcast pitch-level data** (Baseball Savant, via pybaseball): 716,792 regular-season pitches, 2,429 games.
- **MLB Stats API**: teams, daily 40-man roster snapshots, transactions, player profiles, play-by-play (pickoffs, steals).
- **Baseball Savant leaderboards**: sprint speed, catcher pop time, Outs Above Average, catch probability, outfielder jump.
- **Pipeline**: AWS Lambda pulls rosters/transactions every morning → S3 data lake (Parquet) → dbt builds and tests
  every table daily in GitHub Actions → this app reads the finished tables. Infrastructure is defined in Terraform.
- Personal, non-commercial portfolio project; data used under the sources' public terms.

### Key definitions
- **wOBA** (weighted on-base average): overall hitting value per plate appearance. By default, reaching on an error
  counts as an **out**; the sidebar toggle switches to Statcast's convention (counts like a single).
- **xwOBA**: expected wOBA from exit velocity and launch angle; judges contact quality with less luck.
- **Whiff %** = swings and misses ÷ swings (foul tips count as contact). **Chase %** = swings at pitches outside the zone.
  **CSW %** = called strikes + whiffs ÷ pitches.
- **Attack zones** (our implementation of Savant's concept), relative to each batter's own zone:
  heart (< 67% of the way to the edge), shadow/edge (67-133%), chase (133-200%), waste (> 200%).
- **Field zones**: infield/outfield × front/back × left/center/right, cut at 100 / 160 / 275 ft and ±15°,
  using where the ball was fielded.
- **Opportunity** (running game): a plate appearance with a runner on first and second base open.
- **OAA** (Outs Above Average): plays made vs an average fielder given the difficulty (0 = average).
- **Excluded by default**: pitches thrown by position players and pitch-clock automatic balls/strikes (kept and
  flagged in the data, left out of reports because they would mislead).

### "How to attack him" thresholds (rule-based, v1)
| Rule | Threshold |
|---|---|
| Out pitch / most hittable pitch | 100+ pitches; most hittable needs xwOBA on contact ≥ .400 |
| "Sit fastball" when behind | 60%+ fastballs (four-seam, sinker, cutter) when behind, 60+ pitches |
| Two-strike pitch | most-used pitch with two strikes, 60+ pitches |
| Platoon edge (pitcher / hitter) | xwOBA gap ≥ .030 (100+ PA each side) / ≥ .040 (80+ PA each side) |
| Command | heart ≥ 29% → "aggressive early"; ≤ 22% → "lives on the edges" (league 25.6%) |
| Attack with / avoid a pitch type | 50+ pitches seen and 15+ plate appearances ending on it |
| Chases / disciplined | chase swing rate ≥ 3 points above / below league (100+ chase pitches) |
| Swing lengthens vs breaking balls | 0.6+ ft longer than vs fastballs (50+ swings) |
| Pull-heavy / whole field | 50%+ pulled / 33%+ opposite field (100+ batted balls) |
| Will run | steal-attempt rate ≥ 2× league (20+ opportunities) |
| Easy to run on | 85%+ steal success against (10+ attempts) |
| Hot / cold | xwOBA ±.030 vs earlier in the season, 40+ PA in each period |

### Validations (selected)
- Hitter and pitcher tables reconcile exactly (181,220 plate appearances; 711,956 located pitches).
- Game count reconciled to the official MLB schedule (one cancelled game, no missing data).
- Heart pitches are 100% inside Statcast's strike zone; chase and waste are 0%.
- Whiff model: 22% better than a constant baseline in every test month (log-loss), AUC 0.80, calibrated within
  about 1 point; tendencies use only earlier games (leakage-tested).
- Catcher pop time vs caught-stealing rate: -0.58; outfielder jump vs OAA: +0.79.

### What our own tests say about common ideas
- **Hot streaks**: about half of a 30-day streak carries into the next month.
- **Clutch hitting**: not a stable skill in 2026 (first half vs second half correlation 0.02).
- **Whiffs over expected**: not repeatable (0.01); used only as a "likely to cool" flag.

### Known limitations
- Not park-adjusted beyond home/road splits (Coors Field matters).
- Command shows where pitches ended up, not where the catcher set up (targets aren't public).
- Swing-decision run value includes contact results, not decisions alone.
- The pitch planner's per-pitch view uses an approximate swing curve; a dedicated swing model is planned.
- Small samples are flagged (⚠️) but still shown.
""")
