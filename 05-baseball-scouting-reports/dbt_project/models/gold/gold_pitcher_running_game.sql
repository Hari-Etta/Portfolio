-- Gold: each pitcher vs the running game (one row per pitcher). Opportunity = at-bat with a runner on first
-- and second open. throws_per_opp = pickoff throws to first / opportunities. Real pitchers only.
{{ config(
    materialized='external',
    location='s3://' ~ env_var('S3_BUCKET') ~ '/gold/pitcher_running_game.parquet'
) }}

with opp as (
    select pitcher_id, count(distinct concat(game_pk, '-', at_bat_number)) as opps_1b
    from {{ ref('int_pitches') }}
    where runner_on_1b is not null and runner_on_2b is null and not thrown_by_position_player
    group by 1
),

ev as (
    select
        pitcher_id,
        sum(case when category = 'pickoff_throw' then 1 else 0 end)                        as pickoff_throws,
        sum(case when category = 'pickoff_throw' and base = '1B' then 1 else 0 end)        as pickoff_throws_1b,
        sum(case when category = 'pickoff_out' then 1 else 0 end)                          as pickoffs,
        sum(case when category = 'pickoff_error' then 1 else 0 end)                        as pickoff_errors,
        sum(case when is_steal_attempt then 1 else 0 end)                                  as steal_attempts_against,
        sum(case when category = 'stolen_base' then 1 else 0 end)                          as sb_allowed,
        sum(case when category = 'caught_stealing' then 1 else 0 end)                      as cs
    from {{ ref('silver_running_game') }}
    group by 1
)

select
    o.pitcher_id,
    p.display_name                                                   as pitcher_name,
    p.last_team,
    p.throws,
    o.opps_1b,
    coalesce(e.pickoff_throws, 0)                                    as pickoff_throws,
    coalesce(e.pickoff_throws_1b, 0)                                 as pickoff_throws_1b,
    round(1.0 * e.pickoff_throws_1b / nullif(o.opps_1b, 0), 3)       as throws_per_opp,
    coalesce(e.pickoffs, 0)                                          as pickoffs,
    coalesce(e.pickoff_errors, 0)                                    as pickoff_errors,
    coalesce(e.steal_attempts_against, 0)                            as steal_attempts_against,
    coalesce(e.sb_allowed, 0)                                        as sb_allowed,
    coalesce(e.cs, 0)                                                as cs,
    round(1.0 * e.sb_allowed / nullif(e.steal_attempts_against, 0), 3) as sb_pct_against,
    round(1.0 * e.steal_attempts_against / nullif(o.opps_1b, 0), 3)  as attempts_per_opp,
    o.opps_1b < 30                                                   as small_sample
from opp o
left join ev e on o.pitcher_id = e.pitcher_id
left join {{ ref('gold_players') }} p on o.pitcher_id = p.player_id
