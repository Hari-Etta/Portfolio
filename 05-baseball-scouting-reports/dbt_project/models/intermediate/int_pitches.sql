-- Shared base for every gold table: ALL rows, plus names and scouting flags. Every rule is defined ONCE here.
-- thrown_by_position_player: lets each report decide whether to include those pitches (default: exclude).
-- is_pitch_thrown: false for pitch-clock violations (automatic_ball / automatic_strike).
-- Whiff = swing and miss; foul tips count as contact.
-- PA columns: is_pa = wOBA-eligible plate appearance (woba_denom = 1). The *_pts columns are each row's
-- contribution to wOBA: woba_pts counts reached-on-error / fielder's choice as outs (default);
-- woba_statcast_pts follows Statcast (they count like singles); xwoba_pts uses expected value on contact.
-- Teams: home team pitches in the top of the inning. park = home team (the ballpark the game was played in).
-- attack_zone (our implementation of Savant's concept): distance from the zone center relative to zone size,
-- using the larger of the horizontal and vertical ratios. Width = half-plate 0.708 ft + ball radius 0.12 ft;
-- height = each batter's own sz_top/sz_bot (+ ball radius). Bands: heart < 0.67, shadow < 1.33, chase < 2.0, else waste.
{{ config(materialized='view') }}

with base as (
    select
        p.*,
        pit.full_name                                       as pitcher_name,
        bat.full_name                                       as batter_name,
        not pit.is_pitcher                                  as thrown_by_position_player,
        p.description not in ('automatic_ball', 'automatic_strike') as is_pitch_thrown,
        concat(p.balls, '-', p.strikes)                     as count_state,
        p.p_throws = p.stand                                as same_side,
        p.zone between 1 and 9                              as in_zone,
        p.description in (
            'swinging_strike', 'swinging_strike_blocked', 'swinging_pitchout', 'foul', 'foul_tip',
            'hit_into_play', 'foul_bunt', 'missed_bunt', 'bunt_foul_tip'
        )                                                   as is_swing,
        p.description in (
            'swinging_strike', 'swinging_strike_blocked', 'swinging_pitchout', 'missed_bunt'
        )                                                   as is_whiff,
        p.description = 'called_strike'                     as is_called_strike,
        p.description = 'hit_into_play'                     as is_in_play,
        coalesce(p.woba_denom, 0) = 1                       as is_pa,
        greatest(
            abs(p.plate_x) / 0.828,
            abs(p.plate_z - (p.sz_top + p.sz_bot) / 2) / ((p.sz_top - p.sz_bot) / 2 + 0.12)
        )                                                   as zone_ratio
    from {{ ref('silver_pitches') }} p
    join {{ ref('silver_players') }} pit on p.pitcher_id = pit.player_id
    join {{ ref('silver_players') }} bat on p.batter_id  = bat.player_id
)

select
    *,
    is_pa and events in ('strikeout', 'strikeout_double_play')          as is_strikeout,
    is_pa and events = 'walk'                                           as is_walk,
    is_pa and events = 'hit_by_pitch'                                   as is_hbp,
    case when is_pa then
        case when events in ('field_error', 'fielders_choice') then 0 else woba_value end
    end                                                                 as woba_pts,
    case when is_pa then woba_value end                                 as woba_statcast_pts,
    case when is_pa then
        case when is_in_play and xwoba is not null then xwoba else woba_value end
    end                                                                 as xwoba_pts,
    is_pitch_thrown and zone is not null and not in_zone                as is_out_of_zone,
    is_pitch_thrown and zone is not null and not in_zone and is_swing   as is_chase,
    is_in_play and launch_speed >= 95                                   as is_hard_hit,
    inning_topbot = 'Top'                                               as pitcher_is_home,
    case when inning_topbot = 'Top' then home_team else away_team end   as pitcher_team,
    case when inning_topbot = 'Top' then away_team else home_team end   as batter_team,
    home_team                                                           as park,
    case
        when zone_ratio is null   then null
        when zone_ratio < 0.67    then 'heart'
        when zone_ratio < 1.33    then 'shadow'
        when zone_ratio < 2.0     then 'chase'
        else 'waste'
    end                                                                 as attack_zone,
    -- pitch_group: fastball / breaking / offspeed / other (defined once; used by bat tracking and spray charts)
    case
        when pitch_type in ('FF', 'SI', 'FC', 'FA')                 then 'fastball'
        when pitch_type in ('SL', 'ST', 'CU', 'KC', 'SV', 'CS')      then 'breaking'
        when pitch_type in ('CH', 'FS', 'FO', 'SC')                  then 'offspeed'
        else 'other'
    end                                                                 as pitch_group
from base


