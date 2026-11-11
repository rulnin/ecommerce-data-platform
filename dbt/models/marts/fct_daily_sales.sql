with orders as (
    select order_purchase_timestamp::date as purchase_date, count(*) as order_count
    from {{ ref('stg_orders') }} group by 1
), items as (
    select purchase_date, count(*) as item_count, sum(item_price_brl) as item_value_brl,
           sum(freight_value_brl) as freight_value_brl,
           sum(item_price_brl) filter (where order_status = 'delivered') as delivered_item_value_brl
    from {{ ref('fct_order_items') }} group by 1
), payments as (
    select purchase_date, count(*) as payment_count, sum(payment_value_brl) as payment_value_brl
    from {{ ref('fct_payments') }} group by 1
)
select d.date_day as purchase_date, coalesce(o.order_count, 0) as order_count,
       coalesce(i.item_count, 0) as item_count, coalesce(p.payment_count, 0) as payment_count,
       coalesce(i.item_value_brl, 0) as item_value_brl,
       coalesce(i.freight_value_brl, 0) as freight_value_brl,
       coalesce(i.delivered_item_value_brl, 0) as delivered_item_value_brl,
       coalesce(p.payment_value_brl, 0) as payment_value_brl,
       coalesce(i.delivered_item_value_brl, 0) as revenue_brl,
       fx.rate_date as fx_rate_date, fx.rate as brl_per_usd,
       coalesce(i.item_value_brl, 0) / fx.rate as item_value_usd,
       coalesce(p.payment_value_brl, 0) / fx.rate as payment_value_usd
from {{ ref('dim_date') }} d
left join orders o on d.date_day = o.purchase_date
left join items i on d.date_day = i.purchase_date
left join payments p on d.date_day = p.purchase_date
left join lateral (
    select rate_date, rate from {{ ref('stg_fx_rates') }} r
    where r.base_currency = 'USD' and r.quote_currency = 'BRL'
      and r.rate_date between d.date_day - 7 and d.date_day
    order by r.rate_date desc limit 1
) fx on true
