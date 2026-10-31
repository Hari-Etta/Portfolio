-- Gold: what each pitcher throws in every count, split by batter handedness.
-- Grain: pitcher x batter side x count (balls-strikes) x pitch type.
-- count_group is from the PITCHER's view: ahead = more strikes than balls.
-- Same filters as the arsenal: real pitchers, real pitches, tracked pitch types only.
{{ config(
    materialized='external',
    location='s3://' ~ env_var('S3_BUCKET') ~ '/gold/pitcher_usage_by_count.parquet'
) }}

with pitches as (
    select *
    from {{ ref('int_pitches') }}
    where not thrown_by_position_player
      and is_pitch_thrown
      and pitch_type <> 'UN'
),

cells as (
    select
        pitcher_id,
        any_value(pitcher_name)     as pitcher_name,
        stand                       as batter_side,
        count_state,
        balls,
        strikes,
        pitch_type,
        any_value(pitch_name)       as pitch_name,
        count(*)                    as pitches
    from pitches
    group by pitcher_id, stand, count_state, balls, strikes, pitch_type
)

select
    concat_ws('-', pitcher_id, batter_side, count_state, pitch_type)            as usage_id,
    pitcher_id,
    pitcher_name,
    batter_side,
    count_state,
    balls,
    strikes,
    case
        when balls = 0 and strikes = 0 then 'first pitch'
        when strikes > balls           then 'ahead'
        when balls > strikes           then 'behind'
        else 'even'
    end                                                                          as count_group,
    strikes = 2                                                                  as two_strikes,
    pitch_type,
    pitch_name,
    pitches,
    sum(pitches) over (partition by pitcher_id, batter_side, count_state)        as pitches_in_count,
    round(1.0 * pitches / sum(pitches) over (partition by pitcher_id, batter_side, count_state), 4) as usage_pct
from cells
