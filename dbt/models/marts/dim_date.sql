with bounds as (
    select min(order_purchase_timestamp)::date as first_day,
           max(order_purchase_timestamp)::date as last_day
    from {{ ref('stg_orders') }}
)
select d::date as date_day, extract(year from d)::integer as year,
       extract(month from d)::integer as month,
       extract(day from d)::integer as day,
       extract(isodow from d)::integer as iso_day_of_week,
       extract(isodow from d) in (6, 7) as is_weekend
from bounds cross join lateral generate_series(first_day, last_day, interval '1 day') d
