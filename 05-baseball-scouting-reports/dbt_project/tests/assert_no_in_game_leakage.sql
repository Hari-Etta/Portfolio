-- Leakage guard: on a pitcher's FIRST pitch of a game, nothing earlier in that game exists,
-- so "velocity so far today" must be null. Any row returned means the feature sees the current or later pitches.
select pitch_id, pitcher_game_pitch_count, game_velo_vs_norm
from {{ ref('ml_whiff_features') }}
where pitcher_game_pitch_count = 0
  and game_velo_vs_norm is not null
