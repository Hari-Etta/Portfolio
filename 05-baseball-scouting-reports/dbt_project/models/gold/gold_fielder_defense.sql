-- Gold: fielding value per fielder (one row per player), from Baseball Savant leaderboards:
-- Outs Above Average (total, by direction, by batter hand), outfield catch probability by difficulty,
-- and outfielder jump components vs league average (feet). Percent text (e.g. "88%") converted to numbers.
{{ config(
    materialized='external',
    location='s3://' ~ env_var('S3_BUCKET') ~ '/gold/fielder_defense.parquet'
) }}

with oaa as (
    select
        cast(player_id as bigint)                                                        as player_id,
        primary_pos_formatted                                                            as position,
        fielding_runs_prevented,
        outs_above_average                                                               as oaa,
        outs_above_average_infront                                                       as oaa_in_front,
        outs_above_average_lateral_toward3bline                                          as oaa_toward_3b_line,
        outs_above_average_lateral_toward1bline                                          as oaa_toward_1b_line,
        outs_above_average_behind                                                        as oaa_behind,
        outs_above_average_rhh                                                           as oaa_vs_rhh,
        outs_above_average_lhh                                                           as oaa_vs_lhh,
        try_cast(replace(cast(actual_success_rate_formatted as varchar), '%', '') as double)        as success_rate_pct,
        try_cast(replace(cast(adj_estimated_success_rate_formatted as varchar), '%', '') as double) as expected_success_rate_pct
    from {{ source('bronze', 'savant_outs_above_average') }}
),

catch_prob as (
    select
        cast(player_id as bigint)            as player_id,
        n_opp_5stars                         as opps_5star,
        n_5star_percent                      as catch_pct_5star,
        n_opp_4stars                         as opps_4star,
        n_4star_percent                      as catch_pct_4star,
        n_opp_3stars                         as opps_3star,
        n_3star_percent                      as catch_pct_3star,
        n_opp_2stars                         as opps_2star,
        n_2star_percent                      as catch_pct_2star
    from {{ source('bronze', 'savant_outfield_catch_prob') }}
),

jump as (
    select
        cast(resp_fielder_id as bigint)      as player_id,
        rel_league_reaction_distance         as reaction_vs_avg_ft,
        rel_league_burst_distance            as burst_vs_avg_ft,
        rel_league_routing_distance          as route_vs_avg_ft,
        f_bootup_distance                    as jump_ft,
        n                                    as jump_opps
    from {{ source('bronze', 'savant_outfielder_jump') }}
)

select
    o.player_id,
    p.display_name                           as player_name,
    p.last_team,
    o.position,
    o.fielding_runs_prevented,
    o.oaa,
    o.oaa_in_front,
    o.oaa_toward_3b_line,
    o.oaa_toward_1b_line,
    o.oaa_behind,
    o.oaa_vs_rhh,
    o.oaa_vs_lhh,
    o.success_rate_pct,
    o.expected_success_rate_pct,
    c.opps_5star,
    c.catch_pct_5star,
    c.opps_4star,
    c.catch_pct_4star,
    c.opps_3star,
    c.catch_pct_3star,
    c.opps_2star,
    c.catch_pct_2star,
    j.reaction_vs_avg_ft,
    j.burst_vs_avg_ft,
    j.route_vs_avg_ft,
    j.jump_ft,
    j.jump_opps
from oaa o
left join catch_prob c on o.player_id = c.player_id
left join jump j on o.player_id = j.player_id
left join {{ ref('gold_players') }} p on o.player_id = p.player_id
