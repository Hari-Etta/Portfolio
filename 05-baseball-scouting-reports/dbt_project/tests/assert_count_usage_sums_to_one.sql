-- Fails if usage within any pitcher x batter side x count does not sum to 100% (allowing for rounding).
select pitcher_id, batter_side, count_state, sum(usage_pct) as total_usage
from {{ ref('gold_pitcher_usage_by_count') }}
group by pitcher_id, batter_side, count_state
having abs(sum(usage_pct) - 1) > 0.001
