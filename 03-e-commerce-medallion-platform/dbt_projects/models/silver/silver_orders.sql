-- Cleans and conforms the raw bronze orders table: dedupes, types dates, drops rows with no order id.
-- Missing delivery/carrier/approval dates are NOT dropped here — they correlate with
-- canceled/in-transit orders (see data-quality findings), so they're kept and typed as-is.
select distinct
    order_id,
    customer_id,
    order_status,
    cast(order_purchase_timestamp as timestamp) as purchase_ts,
    cast(order_approved_at as timestamp) as approved_ts,
    cast(order_delivered_carrier_date as timestamp) as delivered_carrier_ts,
    cast(order_delivered_customer_date as timestamp) as delivered_ts,
    cast(order_estimated_delivery_date as timestamp) as estimated_delivery_ts
from {{ source('bronze', 'olist_orders_dataset') }}
where order_id is not null