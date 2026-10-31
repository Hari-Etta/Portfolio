-- Gold: each catcher's throwing vs basestealers (one row per catcher), plus Savant pop time and arm strength.
-- Catcher caught-stealing excludes pickoff-caught-stealing (those start with the pitcher's throw).
{{ config(
    materialized='external',
    location='s3://' ~ env_var('S3_BUCKET') ~ '/gold/catcher_defense.parquet'
) }}

with ev as (
    select
        catcher_id,
        sum(case when event_type like 'stolen_base%' then 1 else 0 end)        as sb_allowed,
        sum(case when event_type like 'caught_stealing%' then 1 else 0 end)    as cs
    from {{ ref('silver_running_game') }}
    where catcher_id is not null
    group by 1
),

pop as (
    select
        cast(entity_id as bigint)            as catcher_id,
        pop_2b_sba                           as pop_time_2b,
        pop_2b_sba_count                     as pop_2b_attempts,
        exchange_2b_3b_sba                   as exchange_time,
        maxeff_arm_2b_3b_sba                 as arm_strength
    from {{ source('bronze', 'savant_catcher_poptime') }}
)

select
    e.catcher_id,
    p.display_name                                               as catcher_name,
    p.last_team,
    e.sb_allowed,
    e.cs,
    e.sb_allowed + e.cs                                          as steal_attempts,
    round(1.0 * e.cs / nullif(e.sb_allowed + e.cs, 0), 3)        as cs_rate,
    pp.pop_time_2b,
    pp.pop_2b_attempts,
    pp.exchange_time,
    pp.arm_strength,
    (e.sb_allowed + e.cs) < 20                                   as small_sample
from ev e
left join pop pp on e.catcher_id = pp.catcher_id
left join {{ ref('gold_players') }} p on e.catcher_id = p.player_id
