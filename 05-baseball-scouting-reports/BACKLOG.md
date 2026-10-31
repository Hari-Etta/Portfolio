# Backlog: things to revisit

Items deliberately left as "good for now". Each has the reason it was deferred.

## Definitions and thresholds to tune
- **Spray-chart field zones:** cutoffs are 100 ft (infield front/back), 160 ft (infield/outfield),
  275 ft (outfield front/back) and +/-15 degrees (left/center/right), chosen from 2026 fielding distances. Revisit
  with fielder-positioning data or per-park dimensions.
- **Pitch speed bands** for spray charts (<85, 85-92, 93-96, 97+ mph): simple first cut.
- **Hot/cold thresholds** (+/-.030 xwOBA, 40 PA): backtest shows only about half a streak carries forward. Consider
  shrinking recent form toward baseline, and re-run the backtest from a second date (e.g. Jul 29).
- **Attack zones:** our implementation of Savant's concept (bands at 67/133/200% of the zone). Compare against
  Savant's own attack-zone numbers if they become available to download.
- **Competitive swings** for bat tracking: our approximation (bat speed >= 50 mph, no bunts).

## Better measures
- **Pure swing-decision value:** compare each swing/take to what an average hitter would expect from that pitch
  (model-based), so it measures decisions without contact results. Fits after Phase 3.
- **Park factors:** add Baseball Savant's published Statcast park factors (multi-year, home vs road for the same
  teams). Current home/road split shows Coors Field's effect but doesn't adjust for it.
- **Opponent-quality adjustment** for pitcher and hitter results.

## Open questions
- **40-man rosters showing up to 51 players:** check roster status fields; likely injured-list or end-of-season moves.
- **4 slow pitches (under 50 mph) by real pitchers,** all unlabeled (UN): tracking misreads or something unusual?

## Planned data (Tier 2, with Phase 4)
- Savant leaderboards: sprint speed, catcher pop time, arm strength, fielding (OAA, catch probability).
- MLB play-by-play feed: pickoff attempts, steal attempts and success by runner, pitcher and catcher.
- Batting stance (plate distance, open/closed) if downloadable and allowed; then stance vs HBP rate.
- Per-attempt lead distance and steal timing, if public.

## On hold (owner's call)
- 2024-2025 backfill: multi-season trends and organization effects ("do players improve after joining team X?").
