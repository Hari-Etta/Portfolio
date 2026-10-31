-- Gold: each pitcher vs left- and right-handed hitters (one row per pitcher x batter side).
-- PA = plate appearances counted by wOBA (woba_denom = 1: excludes intentional walks, sac bunts, truncated PAs);
-- numerators only count rows where woba_denom = 1, so top and bottom of every rate match.
-- woba (default): reached-on-error and fielder's choice (batter safe) count as OUTS, since an error means
-- the fielder should have made the play. woba_statcast: Statcast's convention (they count like singles),
-- kept so numbers can be checked against Baseball Savant. xwoba judges contact quality, so errors don't affect it.
-- PA outcomes use every row (a walk can end on a pitch-clock automatic ball);
-- pitch-level rates (whiff, chase) use thrown pitches only. Position players excluded.
{{ config(
    materialized='external',
    location='s3://' ~ env_var('S3_BUCKET') ~ '/gold/pitcher_platoon.parquet'
) }}

with rows as (
    select *
    from {{ ref('int_pitches') }}
    where not thrown_by_position_player
),

agg as (
    select
        pitcher_id,
        any_value(pitcher_name)                                                          as pitcher_name,
        any_value(p_throws)                                                              as throws,
        stand                                                                            as batter_side,
        sum(case when is_pitch_thrown then 1 else 0 end)                                 as pitches,
        sum(case when woba_denom = 1 then 1 else 0 end)                                  as pa,
        sum(case when woba_denom = 1 and events in ('strikeout', 'strikeout_double_play') then 1 else 0 end) as strikeouts,
        sum(case when woba_denom = 1 and events = 'walk' then 1 else 0 end)              as walks,
        sum(case when woba_denom = 1 and events not in ('field_error', 'fielders_choice')
                 then woba_value end)                                                    as woba_num,
        sum(case when woba_denom = 1 then woba_value end)                                as woba_statcast_num,
        sum(case when woba_denom = 1 then
                case when is_in_play and xwoba is not null then xwoba else woba_value end
            end)                                                                         as xwoba_num,
        sum(case when is_pitch_thrown and is_swing then 1 else 0 end)                    as swings,
        sum(case when is_pitch_thrown and is_whiff then 1 else 0 end)                    as whiffs,
        sum(case when is_pitch_thrown and zone is not null and not in_zone then 1 else 0 end) as out_zone,
        sum(case when is_pitch_thrown and zone is not null and not in_zone and is_swing then 1 else 0 end) as chases,
        sum(case when is_in_play then 1 else 0 end)                                      as batted_balls,
        sum(case when is_in_play and launch_speed >= 95 then 1 else 0 end)               as hard_hit
    from rows
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
    round(woba_num / nullif(pa, 0), 3)                           as woba,
    round(woba_statcast_num / nullif(pa, 0), 3)                  as woba_statcast,
    round(xwoba_num / nullif(pa, 0), 3)                          as xwoba,
    round(1.0 * whiffs / nullif(swings, 0), 3)                   as whiff_rate,
    round(1.0 * chases / nullif(out_zone, 0), 3)                 as chase_rate,
    round(1.0 * hard_hit / nullif(batted_balls, 0), 3)           as hard_hit_pct,
    pa < 50                                                      as small_sample
from agg
