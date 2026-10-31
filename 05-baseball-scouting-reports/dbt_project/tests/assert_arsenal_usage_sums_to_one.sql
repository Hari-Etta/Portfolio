-- Fails if any pitcher's pitch-type usage does not sum to 100% (allowing for rounding).
select pitcher_id, sum(usage_pct) as total_usage
from {{ ref('gold_pitcher_arsenal') }}
group by pitcher_id
having abs(sum(usage_pct) - 1) > 0.001
