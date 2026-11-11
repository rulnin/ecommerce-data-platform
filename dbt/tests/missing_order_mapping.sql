select i.order_id from {{ ref('stg_order_items') }} i
left join {{ ref('stg_orders') }} o using(order_id) where o.order_id is null
union all
select p.order_id from {{ ref('stg_order_payments') }} p
left join {{ ref('stg_orders') }} o using(order_id) where o.order_id is null
