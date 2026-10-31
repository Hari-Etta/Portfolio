-- Gold: where each hitter puts the ball in play, by pitcher hand x pitch group x speed band x field zone.
-- Counts (not shares) at this fine grain: the app sums any slice a coach picks, then computes percentages.
{{ config(
    materialized='external',
    location='s3://' ~ env_var('S3_BUCKET') ~ '/gold/hitter_spray.parquet'
) }}

select
    concat_ws('-', batter_id, p_throws, pitch_group, coalesce(velo_band, 'na'), field_zone)  as spray_id,
    batter_id,
    any_value(batter_name)                                       as batter_name,
    p_throws                                                     as pitcher_hand,
    pitch_group,
    coalesce(velo_band, 'na')                                    as velo_band,
    field_zone,
    any_value(depth)                                             as depth,
    any_value(direction)                                         as direction,
    any_value(pull_side)                                         as pull_side,
    count(*)                                                     as batted_balls,
    round(avg(launch_speed), 1)                                  as avg_exit_velo,
    sum(case when is_hard_hit then 1 else 0 end)                 as hard_hit,
    round(avg(xwoba), 3)                                         as avg_xwoba,
    sum(case when is_home_run then 1 else 0 end)                 as home_runs,
    round(avg(landing_distance), 0)                              as avg_landing_distance
from {{ ref('int_batted_balls') }}
where field_zone is not null
group by batter_id, p_throws, pitch_group, coalesce(velo_band, 'na'), field_zone
