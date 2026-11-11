select
    business_key as source_key,
    nullif(data->>'order_id', '') as order_id,
    nullif(data->>'payment_sequential', '')::integer as payment_sequential,
    nullif(data->>'payment_type', '') as payment_type,
    nullif(data->>'payment_installments', '')::integer as payment_installments,
    nullif(data->>'payment_value', '')::numeric(18,2) as payment_value,
    row_hash as source_row_hash,
    loaded_at as source_loaded_at
from {{ source('raw', 'order_payments') }}
