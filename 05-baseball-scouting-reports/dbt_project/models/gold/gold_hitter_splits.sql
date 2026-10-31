-- Gold: each hitter vs left- and right-handed pitchers (one row per batter x pitcher hand).
-- Same definitions as gold_pitcher_platoon (from int_pitches). Position-player pitching excluded.
-- batted_as: the side he hit from (switch hitters change sides by pitcher hand).
{{ config(
    materialized='external',
    location='s3://' ~ env_var('S3_BUCKET') ~ '/gold/hitter_splits.parquet'
) }}

with rows as (
    select *,
        case when inning_topbot = 'Top' then away_team else home_team end as batter_team
    from {{ ref('int_pitches') }}
    where not thrown_by_position_player
),

teams as (
    select batter_id, arg_max(batter_team, game_date) as last_team
    from rows
    group by 1
),

agg as (
    select
        batter_id,
        any_value(batter_name)                                       as batter_name,
        p_throws                                                     as pitcher_hand,
        mode(stand)                                                  as batted_as,
        sum(case when is_pitch_thrown then 1 else 0 end)             as pitches_seen,
        sum(case when is_pa then 1 else 0 end)                       as pa,
        sum(case when is_strikeout then 1 else 0 end)                as strikeouts,
        sum(case when is_walk then 1 else 0 end)                     as walks,
        sum(woba_pts)                                                as woba_num,
        sum(woba_statcast_pts)                                       as woba_statcast_num,
        sum(xwoba_pts)                                               as xwoba_num,
        sum(case when is_pitch_thrown and is_swing then 1 else 0 end) as swings,
        sum(case when is_pitch_thrown and is_whiff then 1 else 0 end) as whiffs,
        sum(case when is_out_of_zone then 1 else 0 end)              as out_zone,
        sum(case when is_chase then 1 else 0 end)                    as chases,
        sum(case when is_in_play then 1 else 0 end)                  as batted_balls,
        sum(case when is_hard_hit then 1 else 0 end)                 as hard_hit
    from rows
    group by batter_id, p_throws
)

select
    concat(a.batter_id, '-', a.pitcher_hand)                     as split_id,
    a.batter_id,
    a.batter_name,
    t.last_team,
    a.pitcher_hand,
    a.batted_as,
    a.pitcher_hand = a.batted_as                                 as same_side,
    a.pitches_seen,
    a.pa,
    round(1.0 * a.strikeouts / nullif(a.pa, 0), 3)               as k_pct,
    round(1.0 * a.walks / nullif(a.pa, 0), 3)                    as bb_pct,
    round(a.woba_num / nullif(a.pa, 0), 3)                       as woba,
    round(a.woba_statcast_num / nullif(a.pa, 0), 3)              as woba_statcast,
    round(a.xwoba_num / nullif(a.pa, 0), 3)                      as xwoba,
    round(1.0 * a.whiffs / nullif(a.swings, 0), 3)               as whiff_rate,
    round(1.0 * a.chases / nullif(a.out_zone, 0), 3)             as chase_rate,
    round(1.0 * a.hard_hit / nullif(a.batted_balls, 0), 3)       as hard_hit_pct,
    a.pa < 50                                                    as small_sample
from agg a
join teams t on a.batter_id = t.batter_id
