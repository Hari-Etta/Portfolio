# Baseball Advance Scouting Report Generator

Automated MLB advance scouting reports: Statcast + MLB Stats API -> AWS S3 data lake -> dbt -> whiff model -> Streamlit app.

## Status
- [ ] Phase 1: AWS setup, one-week local test, full backfill in Actions, quality report documented
- [ ] Phase 2: dbt silver/gold models + tests passing
- [ ] Phase 3: whiff model trained, calibration checked
- [ ] Phase 4: Terraform + Lambda/EventBridge daily pull + scheduled dbt
- [ ] Phase 5: Streamlit app live
- [ ] Phase 6: README, resume bullet, pitch, outreach

## Data & Quality
Local test, first week of 2026 (Mar 25-31): 22,610 pitches, 76 games, 392 pitchers, all regular season.
- 0 duplicate pitch keys
- 75 pitches (0.33%) missing pitch type, velocity and location together (untracked pitches)
- 19 pitches with velocity under 50 or over 106 mph (to investigate: eephus pitches / position players pitching)
- 40-man roster snapshot (2026-10-29): 32 to 51 players per team (to investigate)

Full-season numbers: [pending GitHub Actions backfill]
