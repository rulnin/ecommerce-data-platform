select source_key, order_id from {{ ref('stg_order_items') }}
where price is null or freight_value is null or order_id is null
   or order_item_id is null or product_id is null or seller_id is null
union all
select source_key, order_id from {{ ref('stg_order_payments') }}
where payment_value is null or order_id is null or payment_sequential is null
