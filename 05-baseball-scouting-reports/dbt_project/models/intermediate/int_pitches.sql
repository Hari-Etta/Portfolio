-- Shared base for every gold table: ALL rows, plus names and scouting flags. Every rule is defined ONCE here.
-- thrown_by_position_player: lets each report decide whether to include those pitches (default: exclude).
-- is_pitch_thrown: false for pitch-clock violations (automatic_ball / automatic_strike).
-- Whiff = swing and miss; foul tips count as contact.
-- PA columns: is_pa = wOBA-eligible plate appearance (woba_denom = 1). The *_pts columns are each row's
-- contribution to wOBA: woba_pts counts reached-on-error / fielder's choice as outs (default);
-- woba_statcast_pts follows Statcast (they count like singles); xwoba_pts uses expected value on contact.
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
        coalesce(p.woba_denom, 0) = 1                       as is_pa
    from {{ ref('silver_pitches') }} p
    join {{ ref('silver_players') }} pit on p.pitcher_id = pit.player_id
    join {{ ref('silver_players') }} bat on p.batter_id  = bat.player_id
)

select
    *,
    is_pa and events in ('strikeout', 'strikeout_double_play')          as is_strikeout,
    is_pa and events = 'walk'                                           as is_walk,
    case when is_pa then
        case when events in ('field_error', 'fielders_choice') then 0 else woba_value end
    end                                                                 as woba_pts,
    case when is_pa then woba_value end                                 as woba_statcast_pts,
    case when is_pa then
        case when is_in_play and xwoba is not null then xwoba else woba_value end
    end                                                                 as xwoba_pts,
    is_pitch_thrown and zone is not null and not in_zone                as is_out_of_zone,
    is_pitch_thrown and zone is not null and not in_zone and is_swing   as is_chase,
    is_in_play and launch_speed >= 95                                   as is_hard_hit
from base
