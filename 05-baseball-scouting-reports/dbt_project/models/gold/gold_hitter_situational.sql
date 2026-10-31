-- Gold: each hitter's results by base situation (situations overlap on purpose: runners on 1st and 3rd count
-- toward runner_on_1st, runner_on_3rd and risp). Batting average = hits / at-bats ("chance of a hit").
-- woba_vs_overall = situational wOBA minus the hitter's own overall wOBA. Position-player pitching excluded.
{{ config(
    materialized='external',
    location='s3://' ~ env_var('S3_BUCKET') ~ '/gold/hitter_situational.parquet'
) }}

with pa as (
    select
        batter_id,
        batter_name,
        runner_on_1b,
        runner_on_2b,
        runner_on_3b,
        events,
        is_pa,
        is_strikeout,
        woba_pts,
        xwoba_pts,
        is_pa and events not in ('walk', 'hit_by_pitch', 'sac_fly', 'sac_fly_double_play', 'catcher_interf') as is_ab,
        events in ('single', 'double', 'triple', 'home_run')                                               as is_hit
    from {{ ref('int_pitches') }}
    where events is not null
      and events <> 'truncated_pa'
      and not thrown_by_position_player
),

situations as (
    select * from (values
        ('bases_empty'), ('runner_on_1st'), ('runner_on_2nd'), ('runner_on_3rd'), ('risp'), ('bases_loaded')
    ) as s(situation)
),

tagged as (
    select p.*, s.situation
    from pa p
    cross join situations s
    where case s.situation
        when 'bases_empty'   then p.runner_on_1b is null and p.runner_on_2b is null and p.runner_on_3b is null
        when 'runner_on_1st' then p.runner_on_1b is not null
        when 'runner_on_2nd' then p.runner_on_2b is not null
        when 'runner_on_3rd' then p.runner_on_3b is not null
        when 'risp'          then p.runner_on_2b is not null or p.runner_on_3b is not null
        when 'bases_loaded'  then p.runner_on_1b is not null and p.runner_on_2b is not null and p.runner_on_3b is not null
    end
),

overall as (
    select batter_id, sum(woba_pts) / nullif(sum(case when is_pa then 1 else 0 end), 0) as overall_woba
    from pa
    group by 1
),

agg as (
    select
        batter_id,
        any_value(batter_name)                                       as batter_name,
        situation,
        sum(case when is_pa then 1 else 0 end)                       as pa,
        sum(case when is_ab then 1 else 0 end)                       as ab,
        sum(case when is_hit then 1 else 0 end)                      as hits,
        sum(case when is_strikeout then 1 else 0 end)                as strikeouts,
        sum(woba_pts)                                                as woba_num,
        sum(xwoba_pts)                                               as xwoba_num
    from tagged
    group by batter_id, situation
)

select
    concat(a.batter_id, '-', a.situation)                        as situational_id,
    a.batter_id,
    a.batter_name,
    a.situation,
    a.pa,
    a.ab,
    a.hits,
    round(1.0 * a.hits / nullif(a.ab, 0), 3)                     as batting_avg,
    round(a.woba_num / nullif(a.pa, 0), 3)                       as woba,
    round(a.xwoba_num / nullif(a.pa, 0), 3)                      as xwoba,
    round(1.0 * a.strikeouts / nullif(a.pa, 0), 3)               as k_pct,
    round(o.overall_woba, 3)                                     as overall_woba,
    round(a.woba_num / nullif(a.pa, 0) - o.overall_woba, 3)      as woba_vs_overall,
    a.pa < 30                                                    as small_sample
from agg a
join overall o on a.batter_id = o.batter_id
