select p.source_key as payment_key, p.order_id, p.payment_sequential,
       o.customer_id, o.order_purchase_timestamp::date as purchase_date,
       o.order_status, p.payment_type, p.payment_installments,
       p.payment_value as payment_value_brl
from {{ ref('stg_order_payments') }} p
join {{ ref('stg_orders') }} o on p.order_id = o.order_id
