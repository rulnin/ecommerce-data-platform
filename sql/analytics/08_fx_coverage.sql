-- Q8: How much of the snapshot can actually be converted with stored historical FX?
SELECT count(*) AS calendar_days,
       count(brl_per_usd) AS covered_days,
       sum(order_count) FILTER (WHERE brl_per_usd IS NOT NULL) AS covered_orders,
       sum(order_count) AS total_orders,
       round(100.0 * sum(order_count) FILTER (WHERE brl_per_usd IS NOT NULL) / nullif(sum(order_count), 0), 2) AS order_coverage_pct,
       sum(item_value_brl) FILTER (WHERE brl_per_usd IS NOT NULL) AS covered_item_value_brl,
       sum(item_value_brl) FILTER (WHERE brl_per_usd IS NULL) AS uncovered_item_value_brl,
       round(sum(item_value_usd), 2) AS partial_all_status_item_value_usd
FROM published.fct_daily_sales;
