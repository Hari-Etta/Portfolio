-- Silver: one clean, typed row per regular-season pitch.
-- Bronze is raw and append-only, so it can hold duplicates; this keeps the latest copy of each pitch.
{{ config(
    materialized='external',
    location='s3://' ~ env_var('S3_BUCKET') ~ '/silver/pitches.parquet'
) }}

with source as (
    select * from {{ source('bronze', 'statcast') }}
    where game_type = 'R'
),

deduped as (
    select *
    from source
    qualify row_number() over (
        partition by game_pk, at_bat_number, pitch_number
        order by ingested_at desc
    ) = 1
)

select
    concat_ws('-', game_pk, at_bat_number, pitch_number)   as pitch_id,
    cast(game_pk as bigint)                                as game_pk,
    cast(game_date as date)                                as game_date,
    cast(season as int)                                    as season,
    game_type,
    cast(at_bat_number as int)                             as at_bat_number,
    cast(pitch_number as int)                              as pitch_number,
    cast(inning as int)                                    as inning,
    inning_topbot,
    cast(outs_when_up as int)                              as outs,
    cast(balls as int)                                     as balls,
    cast(strikes as int)                                   as strikes,
    cast(pitcher as bigint)                                as pitcher_id,
    cast(batter as bigint)                                 as batter_id,
    p_throws,
    stand,
    home_team,
    away_team,
    coalesce(pitch_type, 'UN')                             as pitch_type,
    coalesce(pitch_name, 'Unknown')                        as pitch_name,
    pitch_type is null                                     as pitch_untracked,
    try_cast(release_speed as double)                      as release_speed,
    try_cast(release_spin_rate as double)                  as spin_rate,
    try_cast(pfx_x as double)                              as pfx_x,
    try_cast(pfx_z as double)                              as pfx_z,
    try_cast(plate_x as double)                            as plate_x,
    try_cast(plate_z as double)                            as plate_z,
    try_cast(sz_top as double)                             as sz_top,
    try_cast(sz_bot as double)                             as sz_bot,
    try_cast(zone as int)                                  as zone,
    description,
    type                                                   as pitch_result,
    events,
    bb_type,
    try_cast(launch_speed as double)                       as launch_speed,
    try_cast(launch_angle as double)                       as launch_angle,
    try_cast(estimated_woba_using_speedangle as double)    as xwoba,
    try_cast(woba_value as double)                         as woba_value,
    try_cast(woba_denom as double)                         as woba_denom,
    -- Tier 1 additions: batted-ball location, bat tracking, run value, arm slot, defense, runners
    try_cast(hc_x as double)                               as hc_x,
    try_cast(hc_y as double)                               as hc_y,
    try_cast(hit_distance_sc as double)                    as hit_distance,
    try_cast(hit_location as int)                          as hit_location,
    try_cast(bat_speed as double)                          as bat_speed,
    try_cast(swing_length as double)                       as swing_length,
    try_cast(attack_angle as double)                       as attack_angle,
    try_cast(attack_direction as double)                   as attack_direction,
    try_cast(swing_path_tilt as double)                    as swing_path_tilt,
    try_cast(delta_run_exp as double)                      as run_value,
    try_cast(arm_angle as double)                          as arm_angle,
    if_fielding_alignment                                  as if_alignment,
    of_fielding_alignment                                  as of_alignment,
    try_cast(on_1b as bigint)                              as runner_on_1b,
    try_cast(on_2b as bigint)                              as runner_on_2b,
    try_cast(on_3b as bigint)                              as runner_on_3b,
    try_cast(fielder_2 as bigint)                          as catcher_id,
    try_cast(bat_score as int)                             as bat_score,
    try_cast(post_bat_score as int)                        as post_bat_score,
    ingested_at
from deduped
