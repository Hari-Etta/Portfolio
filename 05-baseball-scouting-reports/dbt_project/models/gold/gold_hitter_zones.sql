-- Gold: what each hitter does in each Statcast zone, by pitcher hand (batter x pitcher hand x zone).
-- Same filters as gold_pitcher_locations, so league pitch totals must match between the two tables.
-- seen_pct = share of the pitches he saw (vs that hand) that landed in this zone: how pitchers attack him.
{{ config(
    materialized='external',
    location='s3://' ~ env_var('S3_BUCKET') ~ '/gold/hitter_zones.parquet'
) }}

with cells as (
    select
        batter_id,
        any_value(batter_name)                                       as batter_name,
        p_throws                                                     as pitcher_hand,
        zone,
        count(*)                                                     as pitches_seen,
        sum(case when is_swing then 1 else 0 end)                    as swings,
        sum(case when is_whiff then 1 else 0 end)                    as whiffs,
        sum(case when is_called_strike then 1 else 0 end)            as called_strikes,
        sum(case when is_in_play then 1 else 0 end)                  as batted_balls,
        sum(case when is_hard_hit then 1 else 0 end)                 as hard_hit,
        avg(case when is_in_play then xwoba end)                     as xwoba_contact
    from {{ ref('int_pitches') }}
    where not thrown_by_position_player
      and is_pitch_thrown
      and pitch_type <> 'UN'
      and zone is not null
    group by batter_id, p_throws, zone
)

select
    concat_ws('-', batter_id, pitcher_hand, zone)                                as hitter_zone_id,
    batter_id,
    batter_name,
    pitcher_hand,
    zone,
    zone between 1 and 9                                                         as in_zone,
    case when zone between 1 and 9 then (zone - 1) // 3 end                      as zone_row,
    case when zone between 1 and 9 then (zone - 1) % 3 end                       as zone_col,
    pitches_seen,
    round(1.0 * pitches_seen / sum(pitches_seen) over (partition by batter_id, pitcher_hand), 4) as seen_pct,
    round(1.0 * swings / pitches_seen, 3)                                        as swing_rate,
    round(1.0 * whiffs / nullif(swings, 0), 3)                                   as whiff_rate,
    round(1.0 * called_strikes / pitches_seen, 3)                                as called_strike_rate,
    batted_balls,
    round(1.0 * hard_hit / nullif(batted_balls, 0), 3)                           as hard_hit_pct,
    round(xwoba_contact, 3)                                                      as xwoba_contact
from cells
