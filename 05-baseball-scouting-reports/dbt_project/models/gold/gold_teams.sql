-- Gold: one row per MLB team (latest season), mapping team ID <-> abbreviation <-> full name.
-- Lets the app link transactions (team IDs/names) to players (team abbreviations).
{{ config(
    materialized='external',
    location='s3://' ~ env_var('S3_BUCKET') ~ '/gold/teams.parquet'
) }}

select
    cast(id as bigint)          as team_id,
    abbreviation,
    name,
    "teamName"                  as team_name
from {{ source('bronze', 'teams') }}
qualify row_number() over (partition by id order by season desc) = 1
