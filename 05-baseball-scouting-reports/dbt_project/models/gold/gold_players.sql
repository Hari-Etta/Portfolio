-- Gold: player directory for the app (one row per player), with a display name that is guaranteed unique.
-- Rule: unique names stay as-is; shared names get "(position, last team)", e.g. "Max Muncy (3B, LAD)";
-- if still not unique, the player ID is appended. A unique test on display_name enforces this.
-- last_team = team of the player's most recent appearance (as pitcher or hitter).
{{ config(
    materialized='external',
    location='s3://' ~ env_var('S3_BUCKET') ~ '/gold/players.parquet'
) }}

with appearances as (
    select pitcher_id as player_id, pitcher_team as team, game_date from {{ ref('int_pitches') }}
    union all
    select batter_id, batter_team, game_date from {{ ref('int_pitches') }}
),

last_team as (
    select player_id, arg_max(team, game_date) as last_team
    from appearances
    group by 1
),

named as (
    select
        s.*,
        t.last_team,
        count(*) over (partition by s.full_name) as name_count
    from {{ ref('silver_players') }} s
    left join last_team t on s.player_id = t.player_id
),

labeled as (
    select
        *,
        case
            when name_count = 1 then full_name
            else concat(full_name, ' (', primary_position, ', ', coalesce(last_team, '?'), ')')
        end as label
    from named
)

select
    player_id,
    full_name,
    case
        when count(*) over (partition by label) > 1 then concat(label, ' #', player_id)
        else label
    end                                         as display_name,
    name_count > 1                              as name_shared,
    primary_position,
    position_type,
    is_pitcher,
    throws,
    bats,
    last_team
from labeled
