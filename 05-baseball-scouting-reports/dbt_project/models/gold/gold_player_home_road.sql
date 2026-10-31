-- Gold: home vs road results for every hitter and pitcher (one row per player x role x venue).
-- Shows park effects (e.g. Coors Field) directly; does not adjust for them.
-- Same definitions as the splits tables (from int_pitches). Position-player pitching excluded.
-- Note: neutral-site games (e.g. international series) count for the listed home team.
{{ config(
    materialized='external',
    location='s3://' ~ env_var('S3_BUCKET') ~ '/gold/player_home_road.parquet'
) }}

with rows as (
    select * from {{ ref('int_pitches') }}
    where not thrown_by_position_player
),

pitchers as (
    select
        'pitcher'                                                    as role,
        pitcher_id                                                   as player_id,
        any_value(pitcher_name)                                      as player_name,
        arg_max(pitcher_team, game_date)                             as last_team,
        case when pitcher_is_home then 'home' else 'road' end        as venue,
        sum(case when is_pa then 1 else 0 end)                       as pa,
        sum(case when is_strikeout then 1 else 0 end)                as strikeouts,
        sum(case when is_walk then 1 else 0 end)                     as walks,
        sum(woba_pts)                                                as woba_num,
        sum(woba_statcast_pts)                                       as woba_statcast_num,
        sum(xwoba_pts)                                               as xwoba_num,
        sum(case when is_in_play then 1 else 0 end)                  as batted_balls,
        sum(case when is_hard_hit then 1 else 0 end)                 as hard_hit
    from rows
    group by pitcher_id, pitcher_is_home
),

hitters as (
    select
        'hitter'                                                     as role,
        batter_id                                                    as player_id,
        any_value(batter_name)                                       as player_name,
        arg_max(batter_team, game_date)                              as last_team,
        case when pitcher_is_home then 'road' else 'home' end        as venue,
        sum(case when is_pa then 1 else 0 end)                       as pa,
        sum(case when is_strikeout then 1 else 0 end)                as strikeouts,
        sum(case when is_walk then 1 else 0 end)                     as walks,
        sum(woba_pts)                                                as woba_num,
        sum(woba_statcast_pts)                                       as woba_statcast_num,
        sum(xwoba_pts)                                               as xwoba_num,
        sum(case when is_in_play then 1 else 0 end)                  as batted_balls,
        sum(case when is_hard_hit then 1 else 0 end)                 as hard_hit
    from rows
    group by batter_id, pitcher_is_home
),

combined as (
    select * from pitchers
    union all
    select * from hitters
)

select
    concat_ws('-', role, player_id, venue)                       as home_road_id,
    role,
    player_id,
    player_name,
    last_team,
    venue,
    pa,
    round(1.0 * strikeouts / nullif(pa, 0), 3)                   as k_pct,
    round(1.0 * walks / nullif(pa, 0), 3)                        as bb_pct,
    round(woba_num / nullif(pa, 0), 3)                           as woba,
    round(woba_statcast_num / nullif(pa, 0), 3)                  as woba_statcast,
    round(xwoba_num / nullif(pa, 0), 3)                          as xwoba,
    round(1.0 * hard_hit / nullif(batted_balls, 0), 3)           as hard_hit_pct,
    pa < 50                                                      as small_sample
from combined
