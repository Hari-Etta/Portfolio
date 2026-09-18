-- Null-safe handling of the 88.3% missing title / 58.7% missing comment fields found in raw data:
-- treated as "no comment given," not a data error.
select
    review_id,
    order_id,
    review_score,
    coalesce(review_comment_title, 'no title given') as review_comment_title,
    coalesce(review_comment_message, 'no comment given') as review_comment_message,
    cast(review_creation_date as timestamp) as review_created_ts,
    cast(review_answer_timestamp as timestamp) as review_answered_ts
from {{ source('bronze', 'olist_order_reviews_dataset') }}
where review_id is not null