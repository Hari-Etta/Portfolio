-- Gold: where hitters put the ball in play against each pitcher, by batter side x pitch group x speed band x field zone.
-- For positioning the defense behind him. Counts (not shares), like gold_hitter_spray.
{{ config(
    materialized='external',
    location='s3://' ~ env_var('S3_BUCKET') ~ '/gold/pitcher_spray_allowed.parquet'
) }}

select
    concat_ws('-', pitcher_id, stand, pitch_group, coalesce(velo_band, 'na'), field_zone)   as spray_id,
    pitcher_id,
    any_value(pitcher_name)                                      as pitcher_name,
    stand                                                        as batter_side,
    pitch_group,
    coalesce(velo_band, 'na')                                    as velo_band,
    field_zone,
    any_value(depth)                                             as depth,
    any_value(direction)                                         as direction,
    count(*)                                                     as batted_balls,
    round(avg(launch_speed), 1)                                  as avg_exit_velo,
    sum(case when is_hard_hit then 1 else 0 end)                 as hard_hit,
    round(avg(xwoba), 3)                                         as avg_xwoba,
    sum(case when is_home_run then 1 else 0 end)                 as home_runs
from {{ ref('int_batted_balls') }}
where field_zone is not null
group by pitcher_id, stand, pitch_group, coalesce(velo_band, 'na'), field_zone
