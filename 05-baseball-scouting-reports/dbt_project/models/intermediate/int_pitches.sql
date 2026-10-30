-- Shared base for every gold table: ALL rows, plus names and scouting flags.
-- thrown_by_position_player lets each report decide whether to include those pitches (default: exclude).
-- is_pitch_thrown is false for pitch-clock violations (automatic_ball / automatic_strike): they change the
-- count but no pitch was thrown, so pitch-level reports and the model exclude them.
-- Whiff = swing and miss; foul tips count as contact.
{{ config(materialized='view') }}

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
    p.description = 'hit_into_play'                     as is_in_play
from {{ ref('silver_pitches') }} p
join {{ ref('silver_players') }} pit on p.pitcher_id = pit.player_id
join {{ ref('silver_players') }} bat on p.batter_id  = bat.player_id
