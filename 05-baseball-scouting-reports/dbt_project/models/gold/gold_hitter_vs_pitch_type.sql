-- Gold: each hitter vs each pitch type, split by pitcher hand (batter x pitcher hand x pitch type).
-- Swing/whiff/chase use every thrown, tracked pitch of that type he saw.
-- PA stats (wOBA, xwOBA, K%) use plate appearances that ENDED on that pitch type.
-- Position-player pitching, pitch-clock violations and untracked pitches excluded.
{{ config(
    materialized='external',
    location='s3://' ~ env_var('S3_BUCKET') ~ '/gold/hitter_vs_pitch_type.parquet'
) }}

with agg as (
    select
        batter_id,
        any_value(batter_name)                                       as batter_name,
        p_throws                                                     as pitcher_hand,
        pitch_type,
        any_value(pitch_name)                                        as pitch_name,
        count(*)                                                     as pitches_seen,
        sum(case when is_swing then 1 else 0 end)                    as swings,
        sum(case when is_whiff then 1 else 0 end)                    as whiffs,
        sum(case when is_out_of_zone then 1 else 0 end)              as out_zone,
        sum(case when is_chase then 1 else 0 end)                    as chases,
        sum(case when is_pa then 1 else 0 end)                       as pa_ended,
        sum(case when is_strikeout then 1 else 0 end)                as strikeouts,
        sum(woba_pts)                                                as woba_num,
        sum(xwoba_pts)                                               as xwoba_num,
        sum(case when is_in_play then 1 else 0 end)                  as batted_balls,
        sum(case when is_hard_hit then 1 else 0 end)                 as hard_hit
    from {{ ref('int_pitches') }}
    where not thrown_by_position_player
      and is_pitch_thrown
      and pitch_type <> 'UN'
    group by batter_id, p_throws, pitch_type
)

select
    concat_ws('-', batter_id, pitcher_hand, pitch_type)          as hitter_pitch_id,
    batter_id,
    batter_name,
    pitcher_hand,
    pitch_type,
    pitch_name,
    pitches_seen,
    round(1.0 * swings / pitches_seen, 3)                        as swing_rate,
    round(1.0 * whiffs / nullif(swings, 0), 3)                   as whiff_rate,
    round(1.0 * chases / nullif(out_zone, 0), 3)                 as chase_rate,
    pa_ended,
    round(1.0 * strikeouts / nullif(pa_ended, 0), 3)             as k_pct,
    round(woba_num / nullif(pa_ended, 0), 3)                     as woba,
    round(xwoba_num / nullif(pa_ended, 0), 3)                    as xwoba,
    round(1.0 * hard_hit / nullif(batted_balls, 0), 3)           as hard_hit_pct,
    pitches_seen < 50                                            as small_sample
from agg
