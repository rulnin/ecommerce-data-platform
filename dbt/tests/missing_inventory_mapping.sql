select i.product_id from {{ ref('stg_inventory') }} i
left join {{ ref('stg_products') }} p using(product_id) where p.product_id is null
union all
select i.product_id from {{ ref('stg_stock_movements') }} i
left join {{ ref('stg_products') }} p using(product_id) where p.product_id is null
