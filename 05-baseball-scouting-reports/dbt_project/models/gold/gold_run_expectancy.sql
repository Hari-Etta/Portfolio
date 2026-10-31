-- Gold: chance of scoring (and average runs) in the rest of the inning after each plate-appearance outcome,
-- by situation (runners on base x outs). Runs counted from that play onward, including runs scored on the play.
-- Groupings: event x situation, situation only (event = 'ALL', the classic 24 base-out states), event only (situation = 'ALL').
-- Inning-end score uses every row of the half-inning; the table itself excludes position-player pitching and truncated PAs.
-- base_state: '1__' = runner on first, '_2_' = second, '123' = loaded, '___' = empty.
{{ config(
    materialized='external',
    location='s3://' ~ env_var('S3_BUCKET') ~ '/gold/run_expectancy.parquet'
) }}

with innings as (
    select
        *,
        max(post_bat_score) over (partition by game_pk, inning, inning_topbot)   as inning_end_score
    from {{ ref('int_pitches') }}
),

pa_ends as (
    select
        events,
        concat(
            case when runner_on_1b is not null then '1' else '_' end,
            case when runner_on_2b is not null then '2' else '_' end,
            case when runner_on_3b is not null then '3' else '_' end
        )                                                                         as base_state,
        cast(outs as varchar)                                                     as outs_state,
        inning_end_score - bat_score                                              as runs_rest
    from innings
    where events is not null
      and events <> 'truncated_pa'
      and not thrown_by_position_player
),

grouped as (
    select
        coalesce(events, 'ALL')                                                   as event,
        coalesce(base_state, 'ALL')                                               as base_state,
        coalesce(outs_state, 'ALL')                                               as outs,
        count(*)                                                                  as n,
        avg(case when runs_rest > 0 then 1.0 else 0 end)                          as p_score,
        avg(runs_rest)                                                            as avg_runs_rest
    from pa_ends
    group by grouping sets ((events, base_state, outs_state), (base_state, outs_state), (events))
)

select
    concat_ws('|', event, base_state, outs)                                       as re_id,
    event,
    base_state,
    outs,
    n,
    round(p_score, 3)                                                             as p_score,
    round(avg_runs_rest, 3)                                                       as avg_runs_rest,
    n < 50                                                                        as small_sample
from grouped
