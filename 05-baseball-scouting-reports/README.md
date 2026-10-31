# Baseball Advance Scouting Report Generator

Automated MLB advance scouting reports: Statcast + MLB Stats API -> AWS S3 data lake -> dbt -> whiff model -> Streamlit app.

## Status
- [x] Phase 1: AWS setup, one-week local test, full backfill in Actions, quality report documented
- [x] Phase 2: dbt silver/gold models + tests passing
- [x] Scouting additions (Tier 1): home/road, player directory, attack zones, command, swing decisions, bat tracking,
      spray charts, HBP, run expectancy, situational hitting
- [ ] Phase 3: whiff model trained, calibration checked
- [ ] Phase 4: Terraform + Lambda/EventBridge daily pull + scheduled dbt
- [ ] Phase 5: Streamlit app live
- [ ] Phase 6: README, resume bullet, pitch, outreach

Ideas deliberately deferred, with reasons, are tracked in [BACKLOG.md](BACKLOG.md).

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
  2,167 pitches). My first hypothesis (eephus pitches, knuckleballs) was wrong; the data ruled it out.
- **Transactions:** 1,007 duplicate rows from overlapping pulls removed, leaving 10,588 unique transactions.
- **Newer Statcast fields are well populated:** bat speed on 97.4% of swings, batted-ball location on 99.9% of
  balls in play, run value on 99.7% of pitches, arm angle on 99.6% of thrown pitches.
- **Shared names:** 2 names belong to two different players each (Max Muncy, 3B for LAD and ATH; Yunior Marte,
  P for CIN and SF). Display names add position and team; a unique test enforces it.

## Transformations (dbt on S3)
dbt Core 1.12 + dbt-duckdb reads bronze Parquet from S3 and writes silver and gold Parquet back to S3.
22 models, 88 data tests, all passing; the full build runs in under 20 seconds.

**Silver:** `silver_pitches` (716,792 deduplicated, typed pitches; matches bronze exactly) and `silver_players`.

**Shared base:** `int_pitches` defines every rule once (swing, whiff, plate appearance, wOBA contributions, chase,
hard-hit, HBP, teams and park, attack zones, pitch groups); `int_batted_balls` adds spray geometry and field zones.

**Gold (what the app reads):**
| Table | What a coach gets |
|---|---|
| `gold_players` | Player directory with guaranteed-unique display names |
| `gold_pitcher_arsenal` | Pitch mix, velocity, movement, arm angle, whiff / chase / CSW, command (heart / edge / chase / waste %) |
| `gold_pitcher_usage_by_count` | What he throws in every count, vs LHH and RHH |
| `gold_pitcher_locations` | Where each pitch goes (Statcast zones) and what happens there |
| `gold_pitcher_platoon` | Results vs LHH and RHH: K%, BB%, HBP%, wOBA, xwOBA, chase, hard-hit |
| `gold_pitcher_spray_allowed` | Where hitters put the ball against him (12 field zones), for defensive positioning |
| `gold_hitter_splits` | Each hitter vs LHP and RHP, including HBP% |
| `gold_hitter_vs_pitch_type` | Each hitter vs each pitch type |
| `gold_hitter_zones` | Where each hitter swings, misses and does damage |
| `gold_hitter_swing_decisions` | Swing/take decisions and run value by attack zone |
| `gold_hitter_bat_tracking` | Bat speed, swing length, attack angle by pitch group |
| `gold_hitter_spray` | Where each hitter hits it, by pitcher hand, pitch group and pitch speed (12 field zones) |
| `gold_hitter_situational` | Results with runners on each base, vs his own overall level |
| `gold_player_home_road` | Home vs road results (park effects, e.g. Coors Field) |
| `gold_hitter_form` / `gold_pitcher_form` | Last 30 days vs earlier in the season; fastball velocity-drop flag |
| `gold_run_expectancy` | Chance of scoring after each event, by runners on base and outs |
| `gold_transactions` | Deduplicated roster moves for the "what changed" feed |

**Design decisions:**
- **Keep and flag, never delete.** Position-player pitches and pitch-clock violations stay with flags; reports
  exclude them by default because they would mislead a coach.
- **Two wOBA conventions.** Default counts reached-on-error as an out; a Statcast-style column matches Baseball
  Savant. League 2026: .316 (errors as outs), .323 (Statcast style), xwOBA .314.
- **Attack zones** (our implementation of Savant's heart / shadow / chase / waste): bands at 67% / 133% / 200% of
  each batter's own zone.
- **12 field zones:** infield/outfield x front/back x left/center/right (cutoffs 100 / 160 / 275 ft, +/-15 degrees).
- **Counts, not percentages, at fine grain** (spray charts), so the app never shows a misleading share from a tiny cell.
- **Backtesting.** Form tables accept an `as_of_date`.

## Validation beyond tests
- **Reconciliation:** hitter and pitcher tables match exactly: 181,220 plate appearances, 711,956 located pitches,
  122,568 batted balls, and HBP rate (1.16%).
- **Physics and known players:** pitch movement matches pitch types; arm-angle extremes are known submarine and
  sidearm pitchers (Tyler Rogers, -60.6 degrees); fastest bats are known power hitters (league 71.3 mph average,
  25.2% of swings 75+ mph).
- **Spray coordinates:** fielder positions land on the correct side (3B -37 degrees, CF 0, 1B +45); home-run
  distances match Statcast within about 1%; 99% of home runs fall in the deepest outfield zones; pull rates mirror
  for left- and right-handed hitters (43-47% pulled).
- **wOBA level:** first came out 8 points high; traced to Statcast's error convention plus a numerator bug, both fixed.
- **Attack zones vs Statcast:** heart pitches are 100% inside Statcast's strike zone; chase and waste are 0%.
  Swing rate falls from 71.7% (heart) to 7.6% (waste); whiff rate on swings rises from 11.1% to 87.4%.
- **Swing decisions:** league-wide, swinging beats taking only in the heart (+0.37 vs -6.18 runs per 100 pitches);
  taking wins in chase and waste. Run-value sign verified first (HR +1.53, ball +0.05, called strike -0.05).
- **Run expectancy:** chance of scoring rises with runners and falls with outs (bases empty, 0 outs: 27.0%;
  bases loaded, 0 outs: 86.7%), and transitions are consistent (walk with runner on 1st, 0 outs: 61.4% vs the
  1st-and-2nd, 0-out state's 62.1%).
- **Park effects:** Colorado ranks #2 of 30 ballparks by league wOBA (.352), behind the Athletics' temporary park.

## Findings
- **Hot streaks are partly real:** in a backtest from Aug 28, hot hitters went from +.061 xwOBA above baseline to
  +.026 over the next 30 days; cold hitters from -.059 to -.035. Roughly half carries forward.
- **"Clutch" is not a stable skill here:** a hitter's runners-in-scoring-position edge in the first half has
  correlation 0.02 with the second half (199 hitters). Hitters do better with runners on in general (wOBA .310
  bases empty vs .323 runner on 1st), but not in a repeatable player-specific way.
- **HBP is not a patience skill:** HBP rate and walk rate are unrelated (correlation -0.09, 265 hitters), and the
  most-hit batters do not see more inside pitches. Points to the hitter's side (e.g. crowding the plate); stance
  data needed to confirm.
- **After an HBP, teams score in the rest of the inning 41.0% of the time** (vs 37.8% after a walk, 48.1% after a single).
- **Runner on first:** pitchers barely change their mix or velocity, yet hitters gain 16 wOBA points; causes not yet separated.
- **Whiff base rates** (the bar for the Phase 3 model): 10.9% of pitches, 22.9% of swings; always predicting the
  average gives log-loss of about 0.344 per pitch.

## Known limitations
- **Not park-adjusted** beyond the home/road split.
- **Command is where pitches end up, not where they were aimed** (catcher targets are not public).
- **Swing-decision run value includes contact results.**
- **No opponent-quality adjustment.**
- **Spray location is where the ball was fielded,** not always where it first landed (first-landing distance kept separately).

## Planned model rules (Phase 3, to prevent leakage)
- No after-the-pitch inputs (bat speed, swing length, exit velocity, launch angle, hit location, outcome, run value).
- Player tendencies computed only from games before each pitch's date; full-season gold tables are for reports, not features.
- Time-based train/test split, plus a mid-season check so one unusual month can't mislead.
