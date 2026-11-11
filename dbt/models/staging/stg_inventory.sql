select product_id, quantity, is_deleted, updated_at, change_seq, is_synthetic
from {{ source('raw', 'inventory') }}
