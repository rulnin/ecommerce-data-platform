select
    business_key as source_key,
    nullif(data->>'review_id', '') as review_id,
    nullif(data->>'order_id', '') as order_id,
    nullif(data->>'review_score', '')::integer as review_score,
    nullif(data->>'review_comment_title', '') as review_comment_title,
    nullif(data->>'review_comment_message', '') as review_comment_message,
    nullif(data->>'review_creation_date', '')::timestamp as review_creation_date,
    nullif(data->>'review_answer_timestamp', '')::timestamp as review_answer_timestamp,
    row_hash as source_row_hash,
    loaded_at as source_loaded_at
from {{ source('raw', 'order_reviews') }}
