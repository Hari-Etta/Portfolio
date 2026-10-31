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
- **40-man rosters showing up to 51 players (mostly explained):** the API lists 60-day injured players with their team (130 on Oct 31), and they don't count against the 40-man limit in season; the biggest roster (50) has only 34 active. Loose end: one team shows 41 active on Oct 29-31, possibly the post-World Series window to trim rosters. The daily Lambda snapshots will show how it resolves (src/quality/check_roster_status.py).
- **4 slow pitches (under 50 mph) by real pitchers,** all unlabeled (UN): tracking misreads or something unusual?

## Planned data (Tier 2, with Phase 4)
- Savant leaderboards: sprint speed, catcher pop time, arm strength, fielding (OAA, catch probability).
- MLB play-by-play feed: pickoff attempts, steal attempts and success by runner, pitcher and catcher.
- Batting stance (plate distance, open/closed) if downloadable and allowed; then stance vs HBP rate.
- Per-attempt lead distance and steal timing, if public.

## On hold (owner's call)
- 2024-2025 backfill: multi-season trends and organization effects ("do players improve after joining team X?").

## Questions to investigate
- **Why do left-handed hitters pull more?** 2026: lefties pull 46.7% of batted balls vs 43.1% for righties
  (center 28.1% vs 29.1%, opposite 25.2% vs 27.9%). Hypotheses to test, one at a time:
  - **Matchups:** lefties face mostly right-handed pitchers (opposite-handed). Split pull % by pitcher hand
    (same vs opposite side) to see whether the gap is a platoon effect.
  - **Pitch mix and location:** do lefties see more inside pitches or more breaking balls moving toward them?
    Split by pitch group and attack zone.
  - **Batted-ball type:** is the gap in grounders, line drives or fly balls? Split by bb_type.
  - **Who the lefties are:** are left-handed regulars more often power hitters? Compare bat speed and attack direction.
  - **Ballparks:** short right-field fences may reward pulling for lefties. Compare home/road and by park.
- **Is HBP a hitter's strategy (crowding the plate)?** 2026 evidence so far: HBP rate and walk rate are unrelated
  (correlation -0.09 across 265 hitters with 300+ PA), and the most-hit batters do NOT see more inside pitches
  (league 29.3% inside; e.g. 22-27% for several top-HBP hitters). Points to the hitter's side (plate position,
  not moving out of the way) rather than pitchers attacking inside. Confirm with batting-stance data (Tier 2):
  plate distance vs HBP rate. Caveat: "inside" is measured from the plate center, not the batter's body.
- **HBP vs walk scoring:** after an HBP, teams score in the rest of the inning 41.0% of the time vs 37.8% after a walk.
  In the same base-out state they are usually close, but HBP is higher in several (runner on 1st, 0 outs:
  72.3% vs 61.4%, only 130 HBPs). Hypothesis: an HBP signals a pitcher losing control. Test: compare the next
  hitters' results after HBP vs walk with the same pitcher still in.
- **Two-out quirk:** runner on 3rd only scores 25.7% vs 22.5% with runners on 2nd and 3rd. Possibly pitching around
  hitters with first base open; check walk rates in that state.

## Advanced features (end stage)
- **Runner effect on pitchers ("does this runner disturb the pitcher?"):** with a given runner on base, does the
  pitcher's mix (more fastballs), velocity, pickoffs or location change, and do hitters beat expectations?
  Needs sprint speed and pickoff data (Tier 2), runner-level (not batter x runner) samples, and a control for
  pitcher quality, since runners are on base more often when the pitcher is already struggling.
- **Lineup simulator:** simulate innings from run expectancy and player probabilities to compare batting orders.
  Expect small gains (research finds order matters by a handful of runs a season); depends on stable effects.
- **Situational hitting findings (2026):** hitters do better with runners on (wOBA .310 bases empty vs .323 runner on
  1st, .321 RISP). "Clutch" is not a stable skill here: a hitter's RISP-minus-overall wOBA in the first half has
  correlation 0.02 with the second half (199 hitters, 40+ RISP PA each half). Implication: a lineup simulator should
  use overall hitting quality, not situational splits.
- **Runner-on-first effect:** pitchers barely change (fastball 56.4% -> 56.7%, four-seam -0.08 mph), yet hitter wOBA
  rises .310 -> .326. Candidate causes: first baseman holding the runner, or struggling pitchers allowing the runners
  (confounding). Separate them later with fielder alignment, pitcher controls, and sprint speed (Tier 2).

## Model ideas (Phase 3 follow-ups)
- **Fatigue / recent-form features (tested, not adopted):** with reproducible rolling evaluation, the extended set
  was lower in all 4 months but only by ~0.0003 log-loss (0.4176 vs 0.4179) with slightly better calibration
  (0.0064 vs 0.0079). Kept the simpler baseline because three features (pitch count so far, times facing batter,
  velocity so far today) are only known DURING a game, and our reports are pre-game.
- **Pre-game-only extended set:** baseline + 30-day recent form + days rest + season workload. Test with the same
  rolling folds; adopt if it captures most of the calibration gain.
- **Live in-game whiff model:** use the in-game fatigue features for a separate, in-game product.
- **Swing model (version 2):** P(swing) x P(whiff | swing) = P(whiff per pitch), each calibrated.
- **Location-independent "stuff" model:** location drives ~58% of the current model; a model without location
  would rate the pitch itself (velocity, movement, contrast with his fastball).
- **Regularization tuning:** train AUC 0.85 vs test 0.80; try larger min_child_samples / fewer leaves.
- **Whiffs over expected is not a repeatable skill:** cross-fitted expectations are well calibrated (77,815 actual vs
  77,981 expected whiffs), but first-half vs second-half over-performance has correlation 0.01 (338 pitch types).
  Cause: the model already uses each pitcher's past whiff rates, so the residual is mostly luck. Use the table as a
  "due to regress" flag, not a skill measure. A true stuff model must EXCLUDE pitcher/batter tendency features.

