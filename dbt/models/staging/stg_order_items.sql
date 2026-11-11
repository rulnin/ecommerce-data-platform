select
    business_key as source_key,
    nullif(data->>'order_id', '') as order_id,
    nullif(data->>'order_item_id', '')::integer as order_item_id,
    nullif(data->>'product_id', '') as product_id,
    nullif(data->>'seller_id', '') as seller_id,
    nullif(data->>'shipping_limit_date', '')::timestamp as shipping_limit_date,
    nullif(data->>'price', '')::numeric(18,2) as price,
    nullif(data->>'freight_value', '')::numeric(18,2) as freight_value,
    row_hash as source_row_hash,
    loaded_at as source_loaded_at
from {{ source('raw', 'order_items') }}
