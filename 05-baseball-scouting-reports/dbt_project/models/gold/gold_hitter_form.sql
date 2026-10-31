-- Gold: each hitter's last 30 days vs the earlier part of the season (one row per hitter).
-- Window ends at the last game in the data, or at var('as_of_date') for backtesting:
--   dbt show --select gold_hitter_form --vars "{as_of_date: '2026-07-01'}"
-- Baseline = games BEFORE the window, so a streak isn't diluted by including itself.
-- Form label uses xwOBA (contact quality, less luck). v1 rules: hot/cold = +/- .030 xwOBA; min 40 PA in window.
{% set as_of = var('as_of_date', none) %}
{{ config(
    materialized='external',
    location='s3://' ~ env_var('S3_BUCKET') ~ '/gold/hitter_form.parquet'
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
        case when p.inning_topbot = 'Top' then p.away_team else p.home_team end as batter_team
    from {{ ref('int_pitches') }} p
    cross join bounds b
    where not p.thrown_by_position_player
      and p.game_date <= b.as_of_date
),

agg as (
    select
        batter_id,
        any_value(batter_name)                                                   as batter_name,
        arg_max(batter_team, game_date)                                          as last_team,
        any_value(as_of_date)                                                    as as_of_date,
        sum(case when is_pa and not in_window then 1 else 0 end)                 as base_pa,
        sum(case when is_pa and in_window then 1 else 0 end)                     as l30_pa,
        sum(case when not in_window then woba_pts end)                           as base_woba_num,
        sum(case when in_window then woba_pts end)                               as l30_woba_num,
        sum(case when not in_window then xwoba_pts end)                          as base_xwoba_num,
        sum(case when in_window then xwoba_pts end)                              as l30_xwoba_num,
        sum(case when is_strikeout and not in_window then 1 else 0 end)          as base_k,
        sum(case when is_strikeout and in_window then 1 else 0 end)              as l30_k,
        sum(case when is_in_play and not in_window then 1 else 0 end)            as base_bb,
        sum(case when is_in_play and in_window then 1 else 0 end)                as l30_bb,
        sum(case when is_hard_hit and not in_window then 1 else 0 end)           as base_hh,
        sum(case when is_hard_hit and in_window then 1 else 0 end)               as l30_hh
    from rows
    group by batter_id
),

rates as (
    select
        *,
        base_woba_num / nullif(base_pa, 0)      as base_woba,
        l30_woba_num / nullif(l30_pa, 0)        as l30_woba,
        base_xwoba_num / nullif(base_pa, 0)     as base_xwoba,
        l30_xwoba_num / nullif(l30_pa, 0)       as l30_xwoba
    from agg
)

select
    batter_id,
    batter_name,
    last_team,
    as_of_date,
    l30_pa,
    base_pa,
    round(l30_woba, 3)                                          as l30_woba,
    round(base_woba, 3)                                         as base_woba,
    round(l30_xwoba, 3)                                         as l30_xwoba,
    round(base_xwoba, 3)                                        as base_xwoba,
    round(l30_xwoba - base_xwoba, 3)                            as xwoba_change,
    round(1.0 * l30_k / nullif(l30_pa, 0), 3)                   as l30_k_pct,
    round(1.0 * base_k / nullif(base_pa, 0), 3)                 as base_k_pct,
    round(1.0 * l30_hh / nullif(l30_bb, 0), 3)                  as l30_hard_hit_pct,
    round(1.0 * base_hh / nullif(base_bb, 0), 3)                as base_hard_hit_pct,
    case
        when l30_pa < 40 or base_pa < 40           then 'insufficient sample'
        when l30_xwoba - base_xwoba >= 0.030        then 'hot'
        when l30_xwoba - base_xwoba <= -0.030       then 'cold'
        else 'steady'
    end                                                         as form
from rates

