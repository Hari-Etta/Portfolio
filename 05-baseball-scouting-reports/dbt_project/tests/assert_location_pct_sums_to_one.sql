-- Fails if any pitcher x batter side x pitch type's zone shares do not sum to 100% (allowing for rounding).
select pitcher_id, batter_side, pitch_type, sum(location_pct) as total
from {{ ref('gold_pitcher_locations') }}
group by pitcher_id, batter_side, pitch_type
having abs(sum(location_pct) - 1) > 0.002
