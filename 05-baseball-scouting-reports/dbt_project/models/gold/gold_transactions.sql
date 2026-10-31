-- Gold: one row per MLB transaction. Bronze holds overlapping pulls (1,007 duplicate rows from Phase 1
-- test ranges); keep the copy from the most recent pull, since MLB can update records later
-- (e.g. resolutionDate when a player returns from the injured list).
-- IDs arrive as DOUBLE when some values are missing (e.g. no fromTeam on a free-agent signing); cast back to BIGINT.
{{ config(
    materialized='external',
    location='s3://' ~ env_var('S3_BUCKET') ~ '/gold/transactions.parquet'
) }}

with deduped as (
    select *
    from {{ source('bronze', 'transactions') }}
    qualify row_number() over (partition by id order by pulled desc) = 1
)

select
    cast(id as bigint)                          as transaction_id,
    try_cast("date" as date)                    as transaction_date,
    try_cast("effectiveDate" as date)           as effective_date,
    try_cast("resolutionDate" as date)          as resolution_date,
    "typeCode"                                  as type_code,
    "typeDesc"                                  as type_desc,
    description,
    cast("person.id" as bigint)                 as player_id,
    "person.fullName"                           as player_name,
    cast("toTeam.id" as bigint)                 as to_team_id,
    "toTeam.name"                               as to_team_name,
    cast("fromTeam.id" as bigint)               as from_team_id,
    "fromTeam.name"                             as from_team_name,
    pulled                                      as pulled_date
from deduped
