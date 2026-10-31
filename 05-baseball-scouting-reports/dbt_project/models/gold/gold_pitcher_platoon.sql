-- Gold: each pitcher vs left- and right-handed hitters (one row per pitcher x batter side).
-- All definitions (PA, wOBA versions, chase, hard-hit) come from int_pitches, so pitcher and hitter
-- tables always use identical rules. Position players excluded.
{{ config(
    materialized='external',
    location='s3://' ~ env_var('S3_BUCKET') ~ '/gold/pitcher_platoon.parquet'
) }}

with agg as (
    select
        pitcher_id,
        any_value(pitcher_name)                                      as pitcher_name,
        any_value(p_throws)                                          as throws,
        stand                                                        as batter_side,
        sum(case when is_pitch_thrown then 1 else 0 end)             as pitches,
        sum(case when is_pa then 1 else 0 end)                       as pa,
        sum(case when is_strikeout then 1 else 0 end)                as strikeouts,
        sum(case when is_walk then 1 else 0 end)                     as walks,
        sum(case when is_hbp then 1 else 0 end)                      as hbps,
        sum(woba_pts)                                                as woba_num,
        sum(woba_statcast_pts)                                       as woba_statcast_num,
        sum(xwoba_pts)                                               as xwoba_num,
        sum(case when is_pitch_thrown and is_swing then 1 else 0 end) as swings,
        sum(case when is_pitch_thrown and is_whiff then 1 else 0 end) as whiffs,
        sum(case when is_out_of_zone then 1 else 0 end)              as out_zone,
        sum(case when is_chase then 1 else 0 end)                    as chases,
        sum(case when is_in_play then 1 else 0 end)                  as batted_balls,
        sum(case when is_hard_hit then 1 else 0 end)                 as hard_hit
    from {{ ref('int_pitches') }}
    where not thrown_by_position_player
    group by pitcher_id, stand
)

select
    concat(pitcher_id, '-', batter_side)                         as platoon_id,
    pitcher_id,
    pitcher_name,
    throws,
    batter_side,
    throws = batter_side                                         as same_side,
    pitches,
    pa,
    round(1.0 * strikeouts / nullif(pa, 0), 3)                   as k_pct,
    round(1.0 * walks / nullif(pa, 0), 3)                        as bb_pct,
    round(1.0 * hbps / nullif(pa, 0), 3)                         as hbp_pct,
    round(woba_num / nullif(pa, 0), 3)                           as woba,
    round(woba_statcast_num / nullif(pa, 0), 3)                  as woba_statcast,
    round(xwoba_num / nullif(pa, 0), 3)                          as xwoba,
    round(1.0 * whiffs / nullif(swings, 0), 3)                   as whiff_rate,
    round(1.0 * chases / nullif(out_zone, 0), 3)                 as chase_rate,
    round(1.0 * hard_hit / nullif(batted_balls, 0), 3)           as hard_hit_pct,
    pa < 50                                                      as small_sample
from agg


