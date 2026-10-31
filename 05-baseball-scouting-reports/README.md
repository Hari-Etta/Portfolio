# Baseball Advance Scouting Report Generator

Automated MLB advance scouting reports: Statcast + MLB Stats API -> AWS S3 data lake -> dbt -> whiff model -> Streamlit app.

## Status
- [x] Phase 1: AWS setup, one-week local test, full backfill in Actions, quality report documented
- [x] Phase 2: dbt silver/gold models + tests passing
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
- Open item: 40-man roster snapshots show 32 to 51 players per team (more than 40 not yet explained).

## Transformations (dbt on S3)
dbt Core 1.12 + dbt-duckdb reads bronze Parquet from S3 and writes silver and gold Parquet back to S3.
13 models, 62 data tests, all passing; the full build runs in under 15 seconds.

**Silver:** `silver_pitches` (716,792 deduplicated, typed pitches; matches bronze exactly) and `silver_players`.

**Shared base (`int_pitches`):** every rule is defined once (swing, whiff, plate appearance, wOBA contributions,
chase, hard-hit), so pitcher and hitter tables always agree.

**Gold (what the app reads):**
| Table | What a coach gets |
|---|---|
| `gold_pitcher_arsenal` | Pitch mix, velocity, movement, whiff / chase / CSW per pitch type |
| `gold_pitcher_usage_by_count` | What he throws in every count, vs LHH and RHH |
| `gold_pitcher_locations` | Where each pitch goes (Statcast zones) and what happens there |
| `gold_pitcher_platoon` | Results vs LHH and RHH: K%, BB%, wOBA, xwOBA, chase, hard-hit |
| `gold_hitter_splits` | Each hitter vs LHP and RHP |
| `gold_hitter_vs_pitch_type` | Each hitter vs each pitch type |
| `gold_hitter_zones` | Where each hitter swings, misses and does damage |
| `gold_hitter_form` / `gold_pitcher_form` | Last 30 days vs earlier in the season; fastball velocity-drop flag |
| `gold_transactions` | Deduplicated roster moves for the "what changed" feed |

**Design decisions:**
- **Keep and flag, never delete.** Position-player pitches and pitch-clock violations stay in the data with flags;
  reports exclude them by default because they would mislead a coach.
- **Two wOBA conventions.** Default counts reached-on-error as an out (an error means the fielder should have made
  the play); a Statcast-style column matches Baseball Savant for verification. League 2026: .316 (errors as outs),
  .323 (Statcast style), xwOBA .314. Platoon effect: .323 opposite-handed vs .305 same-handed.
- **Backtesting.** Form tables accept an `as_of_date`, so "hot or cold" can be checked as of any date.

**Verification beyond tests:**
- Hitter and pitcher tables reconcile exactly: 181,220 plate appearances and 711,956 located pitches from both sides.
- Pitch movement matches physics (arm-side run on sinkers and changeups, glove-side on sweepers).
- League wOBA was 8 points high at first; traced to Statcast's error convention plus a numerator bug, both fixed.
- A refactor was regression-checked: platoon numbers identical before and after.
- Credentials reach DuckDB through its credential chain, so dbt never sees or prints AWS keys.
