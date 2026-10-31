-- Fails if any hitter x pitcher hand's zone shares do not sum to 100% (allowing for rounding).
select batter_id, pitcher_hand, sum(seen_pct) as total
from {{ ref('gold_hitter_zones') }}
group by batter_id, pitcher_hand
having abs(sum(seen_pct) - 1) > 0.002
