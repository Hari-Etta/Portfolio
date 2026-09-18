-- Fixes the 26.2% duplicate-row problem found in raw geolocation data: collapses to one
-- representative lat/long per zip code prefix instead of joining against duplicated rows.
select
    geolocation_zip_code_prefix as customer_zip_code_prefix,
    avg(geolocation_lat) as avg_lat,
    avg(geolocation_lng) as avg_lng,
    first(geolocation_city) as city,
    first(geolocation_state) as state
from {{ source('bronze', 'olist_geolocation_dataset') }}
group by geolocation_zip_code_prefix