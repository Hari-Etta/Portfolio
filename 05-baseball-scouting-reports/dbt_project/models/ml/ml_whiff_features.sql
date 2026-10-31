-- ML training data: one row per swing (real pitchers, tracked pitches), target is_whiff (whiff per swing).
-- ONLY pre-pitch information as features. Prior tendencies come from ASOF joins on STRICTLY earlier game dates,
-- so no feature can see the pitch's own game or any later game (guarded by assert_no_same_day_leakage).
-- Excluded on purpose (after-the-pitch): bat speed, swing length, exit velocity, launch angle, outcome, run value.
-- Orientation: arm_side_break_in > 0 = toward the pitcher's arm side (lefties flipped);
-- plate_x_away > 0 = away from the batter (left-handed batters flipped); plate_z_norm 0 = bottom of his zone, 1 = top.
{{ config(
    materialized='external',
    location='s3://' ~ env_var('S3_BUCKET') ~ '/ml/whiff_features.parquet'
) }}

with thrown as (
    select *
    from {{ ref('int_pitches') }}
    where not thrown_by_position_player
      and is_pitch_thrown
      and pitch_type <> 'UN'
),

swings as (
    select *
    from thrown
    where is_swing
      and release_speed is not null
      and plate_x is not null and plate_z is not null
      and sz_top is not null and sz_bot is not null
),

-- Pitcher's fastball profile (FF/SI/FC), cumulative through each date
fb_daily as (
    select
        pitcher_id,
        game_date,
        count(*)                                                             as n,
        sum(release_speed)                                                   as velo,
        sum(pfx_z) * 12                                                      as ivb,
        sum(case when p_throws = 'R' then -pfx_x else pfx_x end) * 12        as hb
    from thrown
    where pitch_group = 'fastball' and release_speed is not null and pfx_x is not null and pfx_z is not null
    group by 1, 2
),
fb_cum as (
    select
        pitcher_id,
        game_date,
        sum(velo) over w / sum(n) over w                                     as fb_velo,
        sum(ivb)  over w / sum(n) over w                                     as fb_ivb,
        sum(hb)   over w / sum(n) over w                                     as fb_hb
    from fb_daily
    window w as (partition by pitcher_id order by game_date rows between unbounded preceding and current row)
),

-- Batter tendencies (overall and vs pitch group), cumulative through each date
bat_daily as (
    select batter_id, game_date, count(*) as swings, sum(case when is_whiff then 1 else 0 end) as whiffs
    from thrown where is_swing group by 1, 2
),
bat_cum as (
    select batter_id, game_date, sum(swings) over w as prior_swings, sum(whiffs) over w as prior_whiffs
    from bat_daily
    window w as (partition by batter_id order by game_date rows between unbounded preceding and current row)
),
batgrp_daily as (
    select batter_id, pitch_group, game_date, count(*) as swings, sum(case when is_whiff then 1 else 0 end) as whiffs
    from thrown where is_swing group by 1, 2, 3
),
batgrp_cum as (
    select batter_id, pitch_group, game_date, sum(swings) over w as prior_swings, sum(whiffs) over w as prior_whiffs
    from batgrp_daily
    window w as (partition by batter_id, pitch_group order by game_date rows between unbounded preceding and current row)
),

-- Pitcher tendencies (overall and for this pitch type), cumulative through each date
pit_daily as (
    select pitcher_id, game_date, count(*) as swings, sum(case when is_whiff then 1 else 0 end) as whiffs
    from thrown where is_swing group by 1, 2
),
pit_cum as (
    select pitcher_id, game_date, sum(swings) over w as prior_swings, sum(whiffs) over w as prior_whiffs
    from pit_daily
    window w as (partition by pitcher_id order by game_date rows between unbounded preceding and current row)
),
pittype_daily as (
    select pitcher_id, pitch_type, game_date, count(*) as swings, sum(case when is_whiff then 1 else 0 end) as whiffs
    from thrown where is_swing group by 1, 2, 3
),
pittype_cum as (
    select pitcher_id, pitch_type, game_date, sum(swings) over w as prior_swings, sum(whiffs) over w as prior_whiffs
    from pittype_daily
    window w as (partition by pitcher_id, pitch_type order by game_date rows between unbounded preceding and current row)
)

select
    s.pitch_id,
    s.game_date,
    s.pitcher_id,
    s.batter_id,
    case when s.is_whiff then 1 else 0 end                                   as is_whiff,

    -- pitch
    s.pitch_type,
    s.pitch_group,
    s.release_speed,
    s.spin_rate,
    s.arm_angle,
    s.pfx_z * 12                                                             as ivb_in,
    (case when s.p_throws = 'R' then -s.pfx_x else s.pfx_x end) * 12         as arm_side_break_in,

    -- location (batter-relative)
    case when s.stand = 'R' then s.plate_x else -s.plate_x end               as plate_x_away,
    (s.plate_z - s.sz_bot) / nullif(s.sz_top - s.sz_bot, 0)                  as plate_z_norm,
    s.zone_ratio,
    s.attack_zone,

    -- contrast with his own fastball (earlier dates only)
    s.release_speed - fb.fb_velo                                             as velo_diff_fb,
    s.pfx_z * 12 - fb.fb_ivb                                                 as ivb_diff_fb,
    (case when s.p_throws = 'R' then -s.pfx_x else s.pfx_x end) * 12 - fb.fb_hb as hb_diff_fb,

    -- situation
    s.balls,
    s.strikes,
    s.p_throws,
    s.stand,
    s.same_side,

    -- tendencies (earlier dates only)
    b.prior_swings                                                           as bat_prior_swings,
    b.prior_whiffs / nullif(b.prior_swings, 0)                               as bat_prior_whiff_rate,
    bg.prior_swings                                                          as bat_grp_prior_swings,
    bg.prior_whiffs / nullif(bg.prior_swings, 0)                             as bat_grp_prior_whiff_rate,
    p.prior_swings                                                           as pit_prior_swings,
    p.prior_whiffs / nullif(p.prior_swings, 0)                               as pit_prior_whiff_rate,
    pt.prior_swings                                                          as pit_type_prior_swings,
    pt.prior_whiffs / nullif(pt.prior_swings, 0)                             as pit_type_prior_whiff_rate

from swings s
asof left join fb_cum fb
    on s.pitcher_id = fb.pitcher_id and s.game_date > fb.game_date
asof left join bat_cum b
    on s.batter_id = b.batter_id and s.game_date > b.game_date
asof left join batgrp_cum bg
    on s.batter_id = bg.batter_id and s.pitch_group = bg.pitch_group and s.game_date > bg.game_date
asof left join pit_cum p
    on s.pitcher_id = p.pitcher_id and s.game_date > p.game_date
asof left join pittype_cum pt
    on s.pitcher_id = pt.pitcher_id and s.pitch_type = pt.pitch_type and s.game_date > pt.game_date
