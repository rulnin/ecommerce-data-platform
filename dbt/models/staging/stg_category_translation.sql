select
    business_key as source_key,
    nullif(data->>'product_category_name', '') as product_category_name,
    nullif(data->>'product_category_name_english', '') as product_category_name_english,
    row_hash as source_row_hash,
    loaded_at as source_loaded_at
from {{ source('raw', 'category_translation') }}
