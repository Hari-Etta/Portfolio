-- Cleans and conforms the raw bronze payments table: dedupes, drops rows with no order id.
select distinct
    order_id,
    payment_sequential,
    payment_type,
    payment_installments,
    payment_value
from {{ source('bronze', 'olist_order_payments_dataset') }}
where order_id is not null