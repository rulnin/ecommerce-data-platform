select movement_id, product_id, delta, is_deleted, updated_at, change_seq, is_synthetic
from {{ source('raw', 'stock_movements') }}
