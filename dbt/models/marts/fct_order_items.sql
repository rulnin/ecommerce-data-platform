{{ config(materialized='incremental', unique_key='order_item_key',
          incremental_strategy='delete+insert', on_schema_change='fail',
          indexes=[{'columns': ['order_item_key'], 'unique': true}]) }}
with current_items as (
    select i.source_key as order_item_key, i.order_id, i.order_item_id,
           i.product_id, i.seller_id, o.customer_id,
           o.order_purchase_timestamp::date as purchase_date, o.order_status,
           i.price as item_price_brl, i.freight_value as freight_value_brl
    from {{ ref('stg_order_items') }} i
    join {{ ref('stg_orders') }} o on i.order_id = o.order_id
)
select c.* from current_items c
{% if is_incremental() %}
left join {{ this }} t on c.order_item_key = t.order_item_key
where t.order_item_key is null
   or row(c.order_id, c.order_item_id, c.product_id, c.seller_id, c.customer_id,
          c.purchase_date, c.order_status, c.item_price_brl, c.freight_value_brl)
      is distinct from
      row(t.order_id, t.order_item_id, t.product_id, t.seller_id, t.customer_id,
          t.purchase_date, t.order_status, t.item_price_brl, t.freight_value_brl)
{% endif %}
