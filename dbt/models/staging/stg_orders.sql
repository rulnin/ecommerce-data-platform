select
    business_key as source_key,
    nullif(data->>'order_id', '') as order_id,
    nullif(data->>'customer_id', '') as customer_id,
    nullif(data->>'order_status', '') as order_status,
    nullif(data->>'order_purchase_timestamp', '')::timestamp as order_purchase_timestamp,
    nullif(data->>'order_approved_at', '')::timestamp as order_approved_at,
    nullif(data->>'order_delivered_carrier_date', '')::timestamp as order_delivered_carrier_date,
    nullif(data->>'order_delivered_customer_date', '')::timestamp as order_delivered_customer_date,
    nullif(data->>'order_estimated_delivery_date', '')::timestamp as order_estimated_delivery_date,
    row_hash as source_row_hash,
    loaded_at as source_loaded_at
from {{ source('raw', 'orders') }}
