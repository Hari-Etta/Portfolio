-- Gold: each pitcher's arsenal (one row per pitcher x pitch type).
-- Real pitchers and real pitches only: excludes position players, pitch-clock violations,
-- and untracked pitches (UN), which have no velocity or movement to describe.
-- Movement is in inches from the catcher's view; vertical break is induced (gravity removed).
-- Command (attack zones from int_pitches): where pitches END UP, not where they were aimed
-- (catcher targets are not public). Shadow % = edges of the zone, the main command signal.
{{ config(
    materialized='external',
    location='s3://' ~ env_var('S3_BUCKET') ~ '/gold/pitcher_arsenal.parquet'
) }}

with pitches as (
    select *
    from {{ ref('int_pitches') }}
    where not thrown_by_position_player
      and is_pitch_thrown
      and pitch_type <> 'UN'
),

pitcher_team as (
    select pitcher_id, arg_max(pitcher_team, game_date) as last_team
    from pitches
    group by 1
),

by_type as (
    select
        pitcher_id,
        any_value(pitcher_name)                                                  as pitcher_name,
        any_value(p_throws)                                                      as throws,
        pitch_type,
        any_value(pitch_name)                                                    as pitch_name,
        count(*)                                                                 as pitches,
        avg(release_speed)                                                       as avg_velo,
        max(release_speed)                                                       as max_velo,
        avg(spin_rate)                                                           as avg_spin,
        avg(pfx_x) * 12                                                          as horz_break_in,
        avg(pfx_z) * 12                                                          as vert_break_in,
        avg(arm_angle)                                                           as arm_angle,
        sum(case when is_swing then 1 else 0 end)                                as swings,
        sum(case when is_whiff then 1 else 0 end)                                as whiffs,
        sum(case when in_zone then 1 else 0 end)                                 as in_zone_pitches,
        sum(case when zone is not null and not in_zone then 1 else 0 end)        as out_zone_pitches,
        sum(case when zone is not null and not in_zone and is_swing then 1 else 0 end) as chases,
        sum(case when is_called_strike or is_whiff then 1 else 0 end)            as csw,
        avg(case when is_in_play then xwoba end)                                 as xwoba_contact,
        count(attack_zone)                                                       as located,
        sum(case when attack_zone = 'heart'  then 1 else 0 end)                  as heart_n,
        sum(case when attack_zone = 'shadow' then 1 else 0 end)                  as shadow_n,
        sum(case when attack_zone = 'chase'  then 1 else 0 end)                  as chase_n,
        sum(case when attack_zone = 'waste'  then 1 else 0 end)                  as waste_n
    from pitches
    group by pitcher_id, pitch_type
)

select
    concat(b.pitcher_id, '-', b.pitch_type)                                      as arsenal_id,
    b.pitcher_id,
    b.pitcher_name,
    t.last_team,
    b.throws,
    b.pitch_type,
    b.pitch_name,
    b.pitches,
    round(1.0 * b.pitches / sum(b.pitches) over (partition by b.pitcher_id), 4)  as usage_pct,
    round(b.avg_velo, 1)                                                         as avg_velo,
    round(b.max_velo, 1)                                                         as max_velo,
    round(b.avg_spin, 0)                                                         as avg_spin,
    round(b.horz_break_in, 1)                                                    as horz_break_in,
    round(b.vert_break_in, 1)                                                    as vert_break_in,
    round(b.arm_angle, 1)                                                        as arm_angle,
    round(1.0 * b.whiffs / nullif(b.swings, 0), 3)                               as whiff_rate,
    round(1.0 * b.chases / nullif(b.out_zone_pitches, 0), 3)                     as chase_rate,
    round(1.0 * b.in_zone_pitches / b.pitches, 3)                                as zone_rate,
    round(1.0 * b.csw / b.pitches, 3)                                            as csw_rate,
    round(b.xwoba_contact, 3)                                                    as xwoba_contact,
    round(1.0 * b.heart_n  / nullif(b.located, 0), 3)                            as heart_pct,
    round(1.0 * b.shadow_n / nullif(b.located, 0), 3)                            as shadow_pct,
    round(1.0 * b.chase_n  / nullif(b.located, 0), 3)                            as chase_zone_pct,
    round(1.0 * b.waste_n  / nullif(b.located, 0), 3)                            as waste_pct,
    b.pitches < 50                                                               as small_sample
from by_type b
join pitcher_team t on b.pitcher_id = t.pitcher_id
