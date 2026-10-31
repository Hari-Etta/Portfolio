-- One row per ball in play (real pitchers only), with spray geometry and the 12 field zones.
-- Coordinates: home plate at (125.42, 198.27), 2.5 ft per unit (validated: home runs match Statcast distance within 1%).
-- fielded_distance = where the ball was fielded (after bounces/roll); landing_distance = Statcast's first-landing distance.
-- field_zone = depth x direction. Cutoffs (see BACKLOG.md): 100 / 160 / 275 ft; direction split at +/-15 degrees.
{{ config(materialized='view') }}

with bip as (
    select
        *,
        case when hc_x is not null and hc_y < 198.27
             then degrees(atan((hc_x - 125.42) / (198.27 - hc_y))) end                    as spray_angle,
        case when hc_x is not null and hc_y < 198.27
             then 2.5 * sqrt(power(hc_x - 125.42, 2) + power(198.27 - hc_y, 2)) end       as fielded_distance
    from {{ ref('int_pitches') }}
    where is_in_play
      and not thrown_by_position_player
),

zoned as (
    select
        pitch_id,
        game_date,
        batter_id,
        batter_name,
        pitcher_id,
        pitcher_name,
        stand,
        p_throws,
        pitch_type,
        pitch_group,
        release_speed,
        case
            when release_speed is null then null
            when release_speed < 85    then '<85'
            when release_speed < 93    then '85-92'
            when release_speed < 97    then '93-96'
            else '97+'
        end                                                                 as velo_band,
        bb_type,
        launch_speed,
        launch_angle,
        xwoba,
        events,
        events = 'home_run'                                                 as is_home_run,
        is_hard_hit,
        spray_angle,
        fielded_distance,
        hit_distance                                                        as landing_distance,
        case
            when spray_angle is null then null
            when spray_angle < -15   then 'left'
            when spray_angle > 15    then 'right'
            else 'center'
        end                                                                 as direction,
        case
            when fielded_distance is null then null
            when fielded_distance < 100   then 'infield_front'
            when fielded_distance < 160   then 'infield_back'
            when fielded_distance < 275   then 'outfield_front'
            else 'outfield_back'
        end                                                                 as depth
    from bip
)

select
    *,
    case when depth is not null and direction is not null
         then concat(depth, '_', direction) end                             as field_zone,
    case
        when direction is null then null
        when direction = 'center' then 'center'
        when (stand = 'R' and direction = 'left') or (stand = 'L' and direction = 'right') then 'pull'
        else 'opposite'
    end                                                                     as pull_side
from zoned
