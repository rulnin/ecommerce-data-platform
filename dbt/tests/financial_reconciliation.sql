with raw_items as (
 select o.order_purchase_timestamp::date as purchase_date,
        sum(i.price) as item_value_brl, sum(i.freight_value) as freight_value_brl,
        sum(case when o.order_status = 'delivered' then i.price else 0 end) as revenue_brl
 from {{ ref('stg_order_items') }} i join {{ ref('stg_orders') }} o using(order_id) group by 1
), raw_payments as (
 select o.order_purchase_timestamp::date as purchase_date, sum(p.payment_value) as payment_value_brl
 from {{ ref('stg_order_payments') }} p join {{ ref('stg_orders') }} o using(order_id) group by 1
), fact_items as (
 select purchase_date, sum(item_price_brl) as item_value_brl, sum(freight_value_brl) as freight_value_brl
 from {{ ref('fct_order_items') }} group by 1
), fact_payments as (
 select purchase_date, sum(payment_value_brl) as payment_value_brl from {{ ref('fct_payments') }} group by 1
), days as (
 select purchase_date from raw_items union select purchase_date from raw_payments
 union select purchase_date from fact_items union select purchase_date from fact_payments
 union select purchase_date from {{ ref('fct_daily_sales') }}
)
select d.purchase_date
from days d
left join raw_items r using(purchase_date) left join raw_payments p using(purchase_date)
left join fact_items f using(purchase_date) left join fact_payments q using(purchase_date)
left join {{ ref('fct_daily_sales') }} s using(purchase_date)
where s.purchase_date is null
 or coalesce(r.item_value_brl,0) <> coalesce(f.item_value_brl,0)
 or coalesce(r.freight_value_brl,0) <> coalesce(f.freight_value_brl,0)
 or coalesce(p.payment_value_brl,0) <> coalesce(q.payment_value_brl,0)
 or coalesce(r.item_value_brl,0) <> s.item_value_brl
 or coalesce(r.freight_value_brl,0) <> s.freight_value_brl
 or coalesce(p.payment_value_brl,0) <> s.payment_value_brl
 or coalesce(r.revenue_brl,0) <> s.revenue_brl
 or s.revenue_brl <> s.delivered_item_value_brl
