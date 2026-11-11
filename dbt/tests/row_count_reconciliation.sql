with counts as (
 select 'items' as check_name, (select count(*) from {{ ref('stg_order_items') }}) as expected,
 (select count(*) from {{ ref('fct_order_items') }}) as actual,
 (select coalesce(sum(item_count),0) from {{ ref('fct_daily_sales') }}) as daily
 union all select 'payments', (select count(*) from {{ ref('stg_order_payments') }}),
 (select count(*) from {{ ref('fct_payments') }}),
 (select coalesce(sum(payment_count),0) from {{ ref('fct_daily_sales') }})
 union all select 'orders', (select count(*) from {{ ref('stg_orders') }}),
 (select coalesce(sum(order_count),0) from {{ ref('fct_daily_sales') }}),
 (select coalesce(sum(order_count),0) from {{ ref('fct_daily_sales') }})
)
select * from counts where expected <> actual or expected <> daily
