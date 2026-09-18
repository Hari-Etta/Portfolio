-- Cleans and conforms the raw bronze customers table.
select distinct
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix,
    customer_city,
    customer_state
from {{ source('bronze', 'olist_customers_dataset') }}
where customer_id is not null