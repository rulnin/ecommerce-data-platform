select
    business_key as source_key,
    nullif(data->>'customer_id', '') as customer_id,
    nullif(data->>'customer_unique_id', '') as customer_unique_id,
    nullif(data->>'customer_zip_code_prefix', '') as customer_zip_code_prefix,
    nullif(data->>'customer_city', '') as customer_city,
    nullif(data->>'customer_state', '') as customer_state,
    row_hash as source_row_hash,
    loaded_at as source_loaded_at
from {{ source('raw', 'customers') }}
