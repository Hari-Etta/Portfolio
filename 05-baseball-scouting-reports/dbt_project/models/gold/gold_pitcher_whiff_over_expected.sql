-- Gold: whiffs over expected per pitcher x pitch type. Expected = sum of cross-fitted model probabilities
-- (each swing scored by a model that never saw its month), given location, count, pitch shape and matchup.
-- Positive = the pitch gets more misses than its inputs predict (e.g. deception the features don't capture).
{{ config(
    materialized='external',
    location='s3://' ~ env_var('S3_BUCKET') ~ '/gold/pitcher_whiff_over_expected.parquet'
) }}

with s as (
    select
        p.pitcher_id,
        p.pitcher_name,
        p.pitcher_team,
        p.game_date,
        p.pitch_type,
        p.pitch_name,
        case when p.is_whiff then 1 else 0 end      as whiff,
        sc.xwhiff
    from {{ source('ml', 'whiff_scores') }} sc
    join {{ ref('int_pitches') }} p on sc.pitch_id = p.pitch_id
),

agg as (
    select
        pitcher_id,
        any_value(pitcher_name)                     as pitcher_name,
        arg_max(pitcher_team, game_date)            as last_team,
        pitch_type,
        any_value(pitch_name)                       as pitch_name,
        count(*)                                    as swings,
        sum(whiff)                                  as whiffs,
        sum(xwhiff)                                 as xwhiffs
    from s
    group by pitcher_id, pitch_type
)

select
    concat(pitcher_id, '-', pitch_type)                         as woe_id,
    pitcher_id,
    pitcher_name,
    last_team,
    pitch_type,
    pitch_name,
    swings,
    whiffs,
    round(xwhiffs, 1)                                           as xwhiffs,
    round(whiffs - xwhiffs, 1)                                  as whiffs_over_expected,
    round(100.0 * (whiffs - xwhiffs) / swings, 2)               as woe_per_100,
    round(1.0 * whiffs / swings, 3)                             as whiff_rate,
    round(xwhiffs / swings, 3)                                  as xwhiff_rate,
    swings < 50                                                 as small_sample
from agg
