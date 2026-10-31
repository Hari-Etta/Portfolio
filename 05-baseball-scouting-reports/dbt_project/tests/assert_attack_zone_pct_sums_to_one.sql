-- Fails if heart + shadow + chase + waste shares don't sum to 100% for any pitcher x pitch type (allowing for rounding).
select arsenal_id, heart_pct + shadow_pct + chase_zone_pct + waste_pct as total
from {{ ref('gold_pitcher_arsenal') }}
where abs(heart_pct + shadow_pct + chase_zone_pct + waste_pct - 1) > 0.003
