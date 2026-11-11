select
    business_key as source_key,
    nullif(data->>'seller_id', '') as seller_id,
    nullif(data->>'seller_zip_code_prefix', '') as seller_zip_code_prefix,
    nullif(data->>'seller_city', '') as seller_city,
    nullif(data->>'seller_state', '') as seller_state,
    row_hash as source_row_hash,
    loaded_at as source_loaded_at
from {{ source('raw', 'sellers') }}
