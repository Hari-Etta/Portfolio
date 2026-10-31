-- Gold: where each pitch type ends up and what happens there, using Statcast zones
-- (1-9 = strike zone 3x3 from the catcher's view; 11-14 = outside quadrants). Zones are batter-height adjusted.
-- Grain: pitcher x batter side x pitch type x zone. Same filters as the arsenal.
{{ config(
    materialized='external',
    location='s3://' ~ env_var('S3_BUCKET') ~ '/gold/pitcher_locations.parquet'
) }}

with pitches as (
    select *
    from {{ ref('int_pitches') }}
    where not thrown_by_position_player
      and is_pitch_thrown
      and pitch_type <> 'UN'
      and zone is not null
),

cells as (
    select
        pitcher_id,
        any_value(pitcher_name)                                      as pitcher_name,
        stand                                                        as batter_side,
        pitch_type,
        any_value(pitch_name)                                        as pitch_name,
        zone,
        count(*)                                                     as pitches,
        sum(case when is_swing then 1 else 0 end)                    as swings,
        sum(case when is_whiff then 1 else 0 end)                    as whiffs,
        sum(case when is_called_strike then 1 else 0 end)            as called_strikes,
        avg(case when is_in_play then xwoba end)                     as xwoba_contact
    from pitches
    group by pitcher_id, stand, pitch_type, zone
)

select
    concat_ws('-', pitcher_id, batter_side, pitch_type, zone)                     as location_id,
    pitcher_id,
    pitcher_name,
    batter_side,
    pitch_type,
    pitch_name,
    zone,
    zone between 1 and 9                                                          as in_zone,
    case when zone between 1 and 9 then (zone - 1) // 3 end                       as zone_row,
    case when zone between 1 and 9 then (zone - 1) % 3 end                        as zone_col,
    pitches,
    round(1.0 * pitches / sum(pitches) over (partition by pitcher_id, batter_side, pitch_type), 4) as location_pct,
    round(1.0 * swings / pitches, 3)                                              as swing_rate,
    round(1.0 * whiffs / nullif(swings, 0), 3)                                    as whiff_rate,
    round(1.0 * called_strikes / pitches, 3)                                      as called_strike_rate,
    round(xwoba_contact, 3)                                                       as xwoba_contact
from cells
