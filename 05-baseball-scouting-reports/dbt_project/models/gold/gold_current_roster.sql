-- Gold: each player's CURRENT roster status (latest daily 40-man snapshot) plus his most recent roster move.
-- Lets reports flag players who left (free agency, release, trade) or are injured, as of the snapshot date.
{{ config(
    materialized='external',
    location='s3://' ~ env_var('S3_BUCKET') ~ '/gold/current_roster.parquet'
) }}

with all_snaps as (
    select
        cast("person.id" as bigint)              as player_id,
        cast(team_id as bigint)                  as team_id,
        "status.code"                            as status_code,
        "status.description"                     as status_desc,
        cast(snapshot_date as date)              as snapshot_date
    from {{ source('bronze', 'rosters') }}
),

snap as (
    select * from all_snaps
    where snapshot_date = (select max(snapshot_date) from all_snaps)
),

moves as (
    select player_id, type_desc, transaction_date, description
    from {{ ref('gold_transactions') }}
    where player_id is not null
      and type_desc in ('Status Change', 'Optioned', 'Recalled', 'Selected', 'Trade', 'Designated for Assignment',
                        'Claimed Off Waivers', 'Released', 'Outrighted', 'Signed', 'Signed as Free Agent',
                        'Declared Free Agency', 'Acquired')
    qualify row_number() over (partition by player_id order by transaction_date desc, transaction_id desc) = 1
)

select
    p.player_id,
    p.display_name,
    p.last_team,
    t.abbreviation                               as roster_team,
    s.status_code,
    s.status_desc,
    s.player_id is not null                      as on_40_man,
    case
        when s.player_id is null       then 'Not on a 40-man roster'
        when s.status_code = 'A'       then 'Active (40-man)'
        when s.status_code = 'D60'     then '60-day IL'
        when s.status_code = '40M'     then 'On 40-man (inactive)'
        else coalesce(s.status_desc, 'On 40-man')
    end                                          as status_label,
    m.type_desc                                  as last_move,
    m.transaction_date                           as last_move_date,
    m.description                                as last_move_details,
    (select max(snapshot_date) from all_snaps)   as snapshot_date
from {{ ref('gold_players') }} p
left join snap s on p.player_id = s.player_id
left join {{ ref('gold_teams') }} t on s.team_id = t.team_id
left join moves m on p.player_id = m.player_id

