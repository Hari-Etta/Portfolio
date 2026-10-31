-- Gold: how each hitter decides to swing or take, by attack zone (one row per batter x attack zone).
-- run_value (Statcast delta_run_exp) is from the batter's view: positive = good for the batter (verified:
-- HR +1.53, ball +0.05, called strike -0.05, strikeout -0.22).
-- swing_runs = decision + contact result on his swings; take_runs = pitches he let go (incl. the rare HBP).
-- league_swing_rate = all hitters' swing rate in the same zone, for context.
{{ config(
    materialized='external',
    location='s3://' ~ env_var('S3_BUCKET') ~ '/gold/hitter_swing_decisions.parquet'
) }}

with cells as (
    select
        batter_id,
        any_value(batter_name)                                       as batter_name,
        attack_zone,
        count(*)                                                     as pitches,
        sum(case when is_swing then 1 else 0 end)                    as swings,
        sum(case when is_whiff then 1 else 0 end)                    as whiffs,
        sum(case when is_swing then run_value else 0 end)            as swing_runs,
        sum(case when not is_swing then run_value else 0 end)        as take_runs
    from {{ ref('int_pitches') }}
    where not thrown_by_position_player
      and is_pitch_thrown
      and attack_zone is not null
    group by batter_id, attack_zone
)

select
    concat(batter_id, '-', attack_zone)                                          as decision_id,
    batter_id,
    batter_name,
    attack_zone,
    pitches,
    swings,
    round(1.0 * swings / pitches, 3)                                             as swing_rate,
    round(1.0 * sum(swings) over (partition by attack_zone)
              / sum(pitches) over (partition by attack_zone), 3)                 as league_swing_rate,
    round(1.0 * swings / pitches
          - 1.0 * sum(swings) over (partition by attack_zone)
                / sum(pitches) over (partition by attack_zone), 3)               as swing_rate_vs_league,
    round(1.0 * whiffs / nullif(swings, 0), 3)                                   as whiff_rate,
    round(swing_runs, 2)                                                         as swing_runs,
    round(take_runs, 2)                                                          as take_runs,
    round(swing_runs + take_runs, 2)                                             as total_runs,
    round(100.0 * (swing_runs + take_runs) / pitches, 2)                         as runs_per_100,
    pitches < 100                                                                as small_sample
from cells
