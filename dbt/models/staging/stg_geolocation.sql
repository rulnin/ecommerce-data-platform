select
    business_key as source_key,
    nullif(data->>'geolocation_zip_code_prefix', '') as geolocation_zip_code_prefix,
    nullif(data->>'geolocation_lat', '')::numeric(18,6) as geolocation_lat,
    nullif(data->>'geolocation_lng', '')::numeric(18,6) as geolocation_lng,
    nullif(data->>'geolocation_city', '') as geolocation_city,
    nullif(data->>'geolocation_state', '') as geolocation_state,
    row_hash as source_row_hash,
    loaded_at as source_loaded_at
from {{ source('raw', 'geolocation') }}
