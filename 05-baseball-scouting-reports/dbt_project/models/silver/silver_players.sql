-- Silver: one row per player with official position and handedness (MLB Stats API).
-- is_pitcher is true for Pitchers and Two-Way Players; everyone else who pitched is a position player.
{{ config(
    materialized='external',
    location='s3://' ~ env_var('S3_BUCKET') ~ '/silver/players.parquet'
) }}

select
    cast(id as bigint)                                          as player_id,
    "fullName"                                                  as full_name,
    "primaryPosition.abbreviation"                              as primary_position,
    "primaryPosition.type"                                      as position_type,
    "pitchHand.code"                                            as throws,
    "batSide.code"                                              as bats,
    "primaryPosition.type" in ('Pitcher', 'Two-Way Player')     as is_pitcher,
    cast(season as int)                                         as season
from {{ source('bronze', 'people') }}
qualify row_number() over (partition by id order by pulled_at desc) = 1
