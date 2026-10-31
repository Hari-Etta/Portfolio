-- Silver: one row per running-game event (pickoff throws, steals, caught stealing, pickoffs), deduplicated,
-- with a simple category, the catcher (from Statcast, at-bat level), and batting/fielding teams.
-- Pickoff-caught-stealing counts as caught_stealing (a failed steal attempt).
-- matched_statcast = false for events in at-bats with no Statcast pitches (e.g. a runner thrown out for the
-- third out before a pitch was thrown); those keep pitcher/runner but have no catcher or team.
{{ config(
    materialized='external',
    location='s3://' ~ env_var('S3_BUCKET') ~ '/silver/running_game.parquet'
) }}

with ev as (
    select
        *,
        concat_ws('-', game_pk, at_bat_number, source, event_type,
                  coalesce(cast(runner_id as varchar), 'x'), coalesce(cast(event_index as varchar), 'x')) as event_id
    from {{ source('bronze', 'running_game') }}
    qualify row_number() over (
        partition by concat_ws('-', game_pk, at_bat_number, source, event_type,
                               coalesce(cast(runner_id as varchar), 'x'), coalesce(cast(event_index as varchar), 'x'))
        order by ingested_at desc
    ) = 1
),

at_bats as (
    select
        game_pk,
        at_bat_number,
        any_value(catcher_id)                                                    as catcher_id,
        any_value(case when inning_topbot = 'Top' then away_team else home_team end) as batting_team,
        any_value(case when inning_topbot = 'Top' then home_team else away_team end) as fielding_team
    from {{ ref('silver_pitches') }}
    group by 1, 2
)

select
    e.event_id,
    cast(e.game_pk as bigint)                                                    as game_pk,
    cast(e.game_date as date)                                                    as game_date,
    cast(e.season as int)                                                        as season,
    cast(e.at_bat_number as int)                                                 as at_bat_number,
    cast(e.inning as int)                                                        as inning,
    e.half,
    cast(e.pitcher_id as bigint)                                                 as pitcher_id,
    cast(e.batter_id as bigint)                                                  as batter_id,
    cast(e.runner_id as bigint)                                                  as runner_id,
    a.catcher_id,
    a.batting_team,
    a.fielding_team,
    e.source,
    e.event_type,
    case
        when e.event_type = 'pickoff_attempt'                    then 'pickoff_throw'
        when e.event_type like 'stolen_base%'                    then 'stolen_base'
        when e.event_type like 'pickoff_caught_stealing%'        then 'caught_stealing'
        when e.event_type like 'caught_stealing%'                then 'caught_stealing'
        when e.event_type like 'pickoff_error%'                  then 'pickoff_error'
        when e.event_type like 'pickoff%'                        then 'pickoff_out'
    end                                                                          as category,
    (e.event_type like 'stolen_base%' or e.event_type like '%caught_stealing%')  as is_steal_attempt,
    case
        when e.event_type like '%_2b'   then '2B'
        when e.event_type like '%_3b'   then '3B'
        when e.event_type like '%_home' then 'home'
    end                                                                          as target_base,
    e.base,
    e.end_base,
    e.is_out,
    cast(e.balls as int)                                                         as balls,
    cast(e.strikes as int)                                                       as strikes,
    cast(e.outs as int)                                                          as outs,
    e.description,
    a.game_pk is not null                                                        as matched_statcast
from ev e
left join at_bats a
    on cast(e.game_pk as bigint) = a.game_pk and cast(e.at_bat_number as int) = a.at_bat_number
