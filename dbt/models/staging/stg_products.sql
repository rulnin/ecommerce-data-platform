select
    business_key as source_key,
    nullif(data->>'product_id', '') as product_id,
    nullif(data->>'product_category_name', '') as product_category_name,
    nullif(data->>'product_name_lenght', '')::integer as product_name_lenght,
    nullif(data->>'product_description_lenght', '')::integer as product_description_lenght,
    nullif(data->>'product_photos_qty', '')::integer as product_photos_qty,
    nullif(data->>'product_weight_g', '')::integer as product_weight_g,
    nullif(data->>'product_length_cm', '')::integer as product_length_cm,
    nullif(data->>'product_height_cm', '')::integer as product_height_cm,
    nullif(data->>'product_width_cm', '')::integer as product_width_cm,
    row_hash as source_row_hash,
    loaded_at as source_loaded_at
from {{ source('raw', 'products') }}
