# Baseball Advance Scouting Report Generator

Automated MLB advance scouting reports: Statcast + MLB Stats API -> AWS S3 data lake -> dbt -> whiff model -> Streamlit app.

## Status
- [x] Phase 1: AWS setup, one-week local test, full backfill in Actions, quality report documented
- [ ] Phase 2: dbt silver/gold models + tests passing (silver done; gold in progress)
- [ ] Phase 3: whiff model trained, calibration checked
- [ ] Phase 4: Terraform + Lambda/EventBridge daily pull + scheduled dbt
- [ ] Phase 5: Streamlit app live
- [ ] Phase 6: README, resume bullet, pitch, outreach

## Data & Quality
Full 2026 regular season (Mar 25 - Sep 27, 184 game days): 716,792 pitches, 2,429 games, 868 pitchers,
plus MLB Stats API teams, daily 40-man roster snapshots, transactions, and official profiles for all 1,470 players.
Loaded by GitHub Actions into an AWS S3 data lake (Parquet, bronze layer) under a least-privilege IAM user and a
budget alarm. The full-season backfill ran in about a minute and resumes safely after failures.

Quality checks found:
- **Game count reconciled against the official MLB schedule:** 2,430 games scheduled, 2,429 played, all 2,429 present.
  The one gap (BAL at NYY, Sep 27) was cancelled and never played. No Statcast games are missing from the schedule.
- **0 duplicate pitch keys** (game, at-bat, pitch number).
- **2,676 pitches (0.37%)** have no pitch type or plate location; kept and labeled `UN` so per-count totals stay complete.
- **957 pitches under 50 or over 106 mph: 953 (99.6%) were thrown by position players.** 56 position players threw
  2,167 pitches in total, identified from official MLB primary positions. The remaining 4 slow pitches came from real
  pitchers and are unlabeled (`UN`). My first hypothesis (eephus pitches and knuckleballs) was wrong; the data ruled it out.
- **2 games were completed early** (shortened), which matters for per-game stats.
- **40-man roster snapshots** show 32 to 51 players per team (more than 40 still to be explained).

## Transformations (dbt on S3)
dbt Core 1.12 + dbt-duckdb reads bronze Parquet from S3 and writes silver Parquet back to S3.
- `silver_pitches`: one deduplicated, typed row per regular-season pitch (716,792 rows, matches bronze exactly).
- `silver_players`: official position and handedness for all 1,470 players.
- 15 data tests pass, including a unique pitch ID (guards against duplicate ingestion) and relationship tests
  proving every pitcher and batter has an official MLB profile.
- Credentials reach DuckDB through its credential chain, so dbt never sees or prints AWS keys.
