-- Gold: each pitcher's last 30 days vs the earlier part of the season (one row per pitcher).
-- Same window logic as gold_hitter_form (var as_of_date for backtesting). Position players excluded.
-- Form uses xwOBA ALLOWED (lower = better). v1 rules: hot/cold = -/+ .030; min 30 batters faced in window.
-- velo_drop: primary fastball (most-thrown of FF/SI/FC) down 1.0+ mph, with 20+ fastballs in window and 50+ before.
{% set as_of = var('as_of_date', none) %}
{{ config(
    materialized='external',
    location='s3://' ~ env_var('S3_BUCKET') ~ '/gold/pitcher_form.parquet'
) }}

with bounds as (
    select {% if as_of %}max(cast('{{ as_of }}' as date)){% else %}max(game_date){% endif %} as as_of_date
    from {{ ref('int_pitches') }}
),

rows as (
    select
        p.*,
        b.as_of_date,
        p.game_date > b.as_of_date - 30                                        as in_window,
        case when p.inning_topbot = 'Top' then p.home_team else p.away_team end as pitcher_team
    from {{ ref('int_pitches') }} p
    cross join bounds b
    where not p.thrown_by_position_player
      and p.game_date <= b.as_of_date
),

primary_fb as (
    select pitcher_id, arg_max(pitch_type, n) as fb_type
    from (
        select pitcher_id, pitch_type, count(*) as n
        from rows
        where is_pitch_thrown and pitch_type in ('FF', 'SI', 'FC')
        group by 1, 2
    )
    group by 1
),

agg as (
    select
        r.pitcher_id,
        any_value(r.pitcher_name)                                                        as pitcher_name,
        arg_max(r.pitcher_team, r.game_date)                                             as last_team,
        any_value(r.as_of_date)                                                          as as_of_date,
        any_value(f.fb_type)                                                             as fb_type,
        sum(case when r.is_pa and not r.in_window then 1 else 0 end)                     as base_bf,
        sum(case when r.is_pa and r.in_window then 1 else 0 end)                         as l30_bf,
        sum(case when not r.in_window then r.xwoba_pts end)                              as base_xwoba_num,
        sum(case when r.in_window then r.xwoba_pts end)                                  as l30_xwoba_num,
        sum(case when r.is_strikeout and not r.in_window then 1 else 0 end)              as base_k,
        sum(case when r.is_strikeout and r.in_window then 1 else 0 end)                  as l30_k,
        avg(case when r.is_pitch_thrown and r.pitch_type = f.fb_type and not r.in_window then r.release_speed end) as base_fb_velo,
        avg(case when r.is_pitch_thrown and r.pitch_type = f.fb_type and r.in_window then r.release_speed end)     as l30_fb_velo,
        sum(case when r.is_pitch_thrown and r.pitch_type = f.fb_type and not r.in_window then 1 else 0 end)        as base_fb_n,
        sum(case when r.is_pitch_thrown and r.pitch_type = f.fb_type and r.in_window then 1 else 0 end)            as l30_fb_n
    from rows r
    left join primary_fb f on r.pitcher_id = f.pitcher_id
    group by r.pitcher_id
),

rates as (
    select
        *,
        base_xwoba_num / nullif(base_bf, 0)     as base_xwoba,
        l30_xwoba_num / nullif(l30_bf, 0)       as l30_xwoba
    from agg
)

select
    pitcher_id,
    pitcher_name,
    last_team,
    as_of_date,
    l30_bf,
    base_bf,
    round(l30_xwoba, 3)                                         as l30_xwoba_allowed,
    round(base_xwoba, 3)                                        as base_xwoba_allowed,
    round(l30_xwoba - base_xwoba, 3)                            as xwoba_change,
    round(1.0 * l30_k / nullif(l30_bf, 0), 3)                   as l30_k_pct,
    round(1.0 * base_k / nullif(base_bf, 0), 3)                 as base_k_pct,
    fb_type,
    round(l30_fb_velo, 1)                                       as l30_fb_velo,
    round(base_fb_velo, 1)                                      as base_fb_velo,
    round(l30_fb_velo - base_fb_velo, 1)                        as fb_velo_change,
    coalesce(l30_fb_n >= 20 and base_fb_n >= 50
             and l30_fb_velo - base_fb_velo <= -1.0, false)     as velo_drop,
    case
        when l30_bf < 30 or base_bf < 30           then 'insufficient sample'
        when l30_xwoba - base_xwoba <= -0.030       then 'hot'
        when l30_xwoba - base_xwoba >= 0.030        then 'cold'
        else 'steady'
    end                                                         as form
from rates

