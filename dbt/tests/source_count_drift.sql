{% set baseline = var('quality_expected_counts', {'orders': 99441, 'order_items': 112650, 'order_payments': 103886}) %}
{% set tolerance = var('quality_count_tolerance', 0.05) %}
with counts as (
{% for name in ['orders', 'order_items', 'order_payments'] %}
 select '{{ name }}' as check_name, {{ baseline[name] }}::numeric as expected,
        count(*) as actual from {{ ref('stg_' ~ name) }}
 {% if not loop.last %}union all{% endif %}
{% endfor %}
)
select * from counts where abs(actual-expected) > expected * {{ tolerance }}
