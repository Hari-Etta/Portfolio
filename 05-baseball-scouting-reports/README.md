# Baseball Advance Scouting Report Generator

Automated MLB advance scouting reports: Statcast + MLB Stats API -> AWS S3 data lake -> dbt -> whiff model -> Streamlit app.

## Status
- [x] Phase 1: AWS setup, one-week local test, full backfill in Actions, quality report documented
- [x] Phase 2: dbt silver/gold models + tests passing
- [ ] Scouting additions (Tier 1): home/road, player directory, attack zones, command, swing decisions done; bat tracking, spray chart in progress
- [ ] Phase 3: whiff model trained, calibration checked
- [ ] Phase 4: Terraform + Lambda/EventBridge daily pull + scheduled dbt
- [ ] Phase 5: Streamlit app live
- [ ] Phase 6: README, resume bullet, pitch, outreach

## Data & Quality
Full 2026 regular season (Mar 25 - Sep 27, 184 game days): 716,792 pitches, 2,429 games, 868 pitchers,
plus MLB Stats API teams, daily 40-man roster snapshots, transactions, and official profiles for all 1,470 players.
Loaded by GitHub Actions into an AWS S3 data lake (Parquet, bronze layer) under a least-privilege IAM user and a
budget alarm. The full-season backfill runs in about a minute and resumes safely after failures.

Quality findings:
- **Game count reconciled against the official MLB schedule:** 2,430 scheduled, 2,429 played, all 2,429 present.
  The one gap (BAL at NYY, Sep 27) was cancelled and never played.
- **0 duplicate pitch keys** in bronze; a dbt uniqueness test now guards against duplicate ingestion.
- **2,676 untracked pitches (0.37%): 2,309 are pitch-clock violations** (automatic balls/strikes, where no pitch
  is thrown); the other 367 are real pitches the tracking system missed. All kept and flagged, never deleted.
- **957 pitches under 50 or over 106 mph: 953 (99.6%) were thrown by position players** (56 position players,
  2,167 pitches, identified from official MLB positions). My first hypothesis (eephus pitches, knuckleballs) was
  wrong; the data ruled it out.
- **Transactions:** 1,007 duplicate rows from overlapping pulls removed, leaving 10,588 unique transactions.
- **Newer Statcast fields are well populated:** bat speed on 97.4% of swings, batted-ball location on 99.9% of
  balls in play, run value on 99.7% of pitches, arm angle on 99.6% of thrown pitches.
- **Shared names:** 2 names belong to two different players each in 2026 (Max Muncy, 3B for LAD and ATH; Yunior
  Marte, P for CIN and SF). Position alone would not separate them, so display names add position and team, and a
  unique test enforces it.
- Open item: 40-man roster snapshots show 32 to 51 players per team (more than 40 not yet explained).

## Transformations (dbt on S3)
dbt Core 1.12 + dbt-duckdb reads bronze Parquet from S3 and writes silver and gold Parquet back to S3.
16 models, 74 data tests, all passing; the full build runs in about 15 seconds.

**Silver:** `silver_pitches` (716,792 deduplicated, typed pitches; matches bronze exactly) and `silver_players`.

**Shared base (`int_pitches`):** every rule is defined once (swing, whiff, plate appearance, wOBA contributions,
chase, hard-hit, teams and park, attack zones), so every gold table agrees.

**Gold (what the app reads):**
| Table | What a coach gets |
|---|---|
| `gold_players` | Player directory with guaranteed-unique display names |
| `gold_pitcher_arsenal` | Pitch mix, velocity, movement, arm angle, whiff / chase / CSW, and command (heart / edge / chase / waste %) per pitch type |
| `gold_pitcher_usage_by_count` | What he throws in every count, vs LHH and RHH |
| `gold_pitcher_locations` | Where each pitch goes (Statcast zones) and what happens there |
| `gold_pitcher_platoon` | Results vs LHH and RHH: K%, BB%, wOBA, xwOBA, chase, hard-hit |
| `gold_hitter_splits` | Each hitter vs LHP and RHP |
| `gold_hitter_vs_pitch_type` | Each hitter vs each pitch type |
| `gold_hitter_zones` | Where each hitter swings, misses and does damage |
| `gold_hitter_swing_decisions` | Swing/take decisions and run value by attack zone |
| `gold_player_home_road` | Home vs road results for every hitter and pitcher (park effects, e.g. Coors Field) |
| `gold_hitter_form` / `gold_pitcher_form` | Last 30 days vs earlier in the season; fastball velocity-drop flag |
| `gold_transactions` | Deduplicated roster moves for the "what changed" feed |

**Design decisions:**
- **Keep and flag, never delete.** Position-player pitches and pitch-clock violations stay in the data with flags;
  reports exclude them by default because they would mislead a coach.
- **Two wOBA conventions.** Default counts reached-on-error as an out (an error means the fielder should have made
  the play); a Statcast-style column matches Baseball Savant for verification. League 2026: .316 (errors as outs),
  .323 (Statcast style), xwOBA .314. Platoon effect: .323 opposite-handed vs .305 same-handed.
- **Attack zones** (our implementation of Savant's heart / shadow / chase / waste concept): distance from the zone
  center relative to each batter's own zone, with bands at 67% / 133% / 200%.
- **Backtesting.** Form tables accept an `as_of_date`, so "hot or cold" can be checked as of any date.

## Validation beyond tests
- **Reconciliation:** hitter and pitcher tables match exactly: 181,220 plate appearances and 711,956 located pitches.
- **Physics:** pitch movement matches known pitch behavior (arm-side run on sinkers and changeups, glove-side on
  sweepers); arm-angle extremes are known submarine and sidearm pitchers (lowest: Tyler Rogers, -60.6 degrees).
- **wOBA level:** first came out 8 points high; traced to Statcast's error convention plus a numerator bug, both fixed.
- **Regression check:** a refactor left platoon numbers identical before and after.
- **Attack zones vs Statcast:** heart pitches are 100% inside Statcast's strike zone; chase and waste are 0%.
  League split 25.6% heart / 41.3% shadow / 23.1% chase / 9.9% waste. Swing rate falls from 71.7% (heart) to
  7.6% (waste) while whiff rate on swings rises from 11.1% to 87.4%.
- **Swing decisions:** league-wide, swinging beats taking only in the heart (+0.37 vs -6.18 runs per 100 pitches);
  taking wins in chase (+6.32 vs -7.67) and waste (+6.18 vs -12.01). Run-value sign verified first (HR +1.53,
  ball +0.05, called strike -0.05).
- **Park effects:** league wOBA by ballpark ranks Colorado #2 of 30 (.352, about 36 points above league), behind
  the Athletics' temporary minor-league park. This mixes park and home-team quality; proper park factors are a
  planned addition.
- **Do hot streaks last?** Backtest from Aug 28 (labels built only on earlier data, judged on the next 30 days):
  hot hitters (55) were +.061 xwOBA above baseline when labeled and +.026 afterwards; cold hitters (74) went from
  -.059 to -.035; steady (120) stayed flat. Streaks are partly real: roughly half carries forward. One date, so rough.
- **Whiff base rates** (the bar for the Phase 3 model): 10.9% of 712,317 pitches and 22.9% of 339,765 swings.
  Always predicting the average gives log-loss of about 0.344 per pitch (0.538 per swing).

## Known limitations
- **Not park-adjusted** beyond the home/road split; Coors Field affects Rockies hitters and pitchers.
- **Command is where pitches end up, not where they were aimed** (catcher targets are not public).
- **Swing-decision run value includes contact results,** so power hitters score well partly from damage on contact.
- **No opponent-quality adjustment.**

## Planned model rules (Phase 3, to prevent leakage)
- No after-the-pitch inputs (bat speed, swing length, exit velocity, launch angle, hit location, outcome, run value).
- Player tendencies computed only from games before each pitch's date; full-season gold tables are for reports, not features.
- Time-based train/test split, plus a mid-season check so one unusual month can't mislead.
