-- Leakage guard: on a batter's FIRST day with swings, no earlier data exists, so prior stats must be null.
-- Any row returned means a feature is seeing same-day (or later) data.
with first_day as (
    select batter_id, min(game_date) as d
    from {{ ref('int_pitches') }}
    where is_swing and is_pitch_thrown and not thrown_by_position_player and pitch_type <> 'UN'
    group by 1
)
select f.pitch_id, f.batter_id, f.game_date, f.bat_prior_swings
from {{ ref('ml_whiff_features') }} f
join first_day d on f.batter_id = d.batter_id and f.game_date = d.d
where f.bat_prior_swings is not null
