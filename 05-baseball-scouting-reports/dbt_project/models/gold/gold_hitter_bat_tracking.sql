-- Gold: each hitter's swing characteristics (bat tracking), per pitch group plus an 'all' row.
-- Competitive swings only (our approximation of Savant's idea): swings with bat speed recorded, at least 50 mph,
-- excluding bunts. Fast swing = 75+ mph (Savant's threshold). Position-player pitching and pitch-clock rows excluded.
{{ config(
    materialized='external',
    location='s3://' ~ env_var('S3_BUCKET') ~ '/gold/hitter_bat_tracking.parquet'
) }}

with swings as (
    select *
    from {{ ref('int_pitches') }}
    where not thrown_by_position_player
      and is_pitch_thrown
      and is_swing
      and bat_speed is not null
      and bat_speed >= 50
      and description not in ('foul_bunt', 'missed_bunt', 'bunt_foul_tip')
      and coalesce(events, '') not in ('sac_bunt', 'sac_bunt_double_play')
),

agg as (
    select
        batter_id,
        any_value(batter_name)                                       as batter_name,
        coalesce(pitch_group, 'all')                                 as pitch_group,
        count(*)                                                     as competitive_swings,
        avg(bat_speed)                                               as avg_bat_speed,
        quantile_cont(bat_speed, 0.9)                                as top_bat_speed,
        avg(case when bat_speed >= 75 then 1.0 else 0 end)           as fast_swing_rate,
        avg(swing_length)                                            as avg_swing_length,
        avg(attack_angle)                                            as avg_attack_angle,
        avg(attack_direction)                                        as avg_attack_direction,
        avg(swing_path_tilt)                                         as avg_swing_path_tilt
    from swings
    group by batter_id, rollup(pitch_group)
    having batter_id is not null
)

select
    concat(batter_id, '-', pitch_group)                          as bat_tracking_id,
    batter_id,
    batter_name,
    pitch_group,
    competitive_swings,
    round(avg_bat_speed, 1)                                      as avg_bat_speed,
    round(top_bat_speed, 1)                                      as top_bat_speed,
    round(fast_swing_rate, 3)                                    as fast_swing_rate,
    round(avg_swing_length, 2)                                   as avg_swing_length,
    round(avg_attack_angle, 1)                                   as avg_attack_angle,
    round(avg_attack_direction, 1)                               as avg_attack_direction,
    round(avg_swing_path_tilt, 1)                                as avg_swing_path_tilt,
    competitive_swings < 50                                      as small_sample
from agg
