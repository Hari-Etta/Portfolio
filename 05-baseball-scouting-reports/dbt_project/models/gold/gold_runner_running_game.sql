-- Gold: each runner's basestealing (one row per runner). Opportunity = at-bat with him on first and second open.
-- attempt_rate_2b = steal attempts of second / opportunities. Sprint speed from Baseball Savant.
{{ config(
    materialized='external',
    location='s3://' ~ env_var('S3_BUCKET') ~ '/gold/runner_running_game.parquet'
) }}

with opp as (
    select runner_on_1b as runner_id, count(distinct concat(game_pk, '-', at_bat_number)) as opps_2b
    from {{ ref('int_pitches') }}
    where runner_on_1b is not null and runner_on_2b is null
    group by 1
),

ev as (
    select
        runner_id,
        sum(case when is_steal_attempt then 1 else 0 end)                                  as attempts,
        sum(case when category = 'stolen_base' then 1 else 0 end)                          as sb,
        sum(case when category = 'caught_stealing' then 1 else 0 end)                      as cs,
        sum(case when is_steal_attempt and target_base = '2B' then 1 else 0 end)           as att_2b,
        sum(case when category = 'stolen_base' and target_base = '2B' then 1 else 0 end)   as sb_2b,
        sum(case when is_steal_attempt and target_base = '3B' then 1 else 0 end)           as att_3b,
        sum(case when category = 'stolen_base' and target_base = '3B' then 1 else 0 end)   as sb_3b,
        sum(case when category = 'pickoff_out' then 1 else 0 end)                          as picked_off
    from {{ ref('silver_running_game') }}
    where runner_id is not null
    group by 1
),

speed as (
    select cast(player_id as bigint) as player_id, sprint_speed, hp_to_1b, competitive_runs, bolts
    from {{ source('bronze', 'savant_sprint_speed') }}
),

runners as (
    select coalesce(e.runner_id, o.runner_id) as runner_id, o.opps_2b, e.*
    exclude (runner_id)
    from ev e
    full outer join opp o on e.runner_id = o.runner_id
)

select
    r.runner_id,
    p.display_name                                               as runner_name,
    p.last_team,
    coalesce(r.opps_2b, 0)                                       as opps_2b,
    coalesce(r.attempts, 0)                                      as attempts,
    coalesce(r.sb, 0)                                            as sb,
    coalesce(r.cs, 0)                                            as cs,
    round(1.0 * r.sb / nullif(r.attempts, 0), 3)                 as sb_pct,
    coalesce(r.att_2b, 0)                                        as att_2b,
    round(1.0 * r.att_2b / nullif(r.opps_2b, 0), 3)              as attempt_rate_2b,
    coalesce(r.att_3b, 0)                                        as att_3b,
    coalesce(r.sb_3b, 0)                                         as sb_3b,
    coalesce(r.picked_off, 0)                                    as picked_off,
    s.sprint_speed,
    s.hp_to_1b,
    s.bolts,
    coalesce(r.opps_2b, 0) < 20                                  as small_sample
from runners r
left join {{ ref('gold_players') }} p on r.runner_id = p.player_id
left join speed s on r.runner_id = s.player_id
