-- Q2: How do delivered sales and value per delivered order vary by purchase month?
WITH delivered AS (
    SELECT date_trunc('month', purchase_date)::date AS purchase_month,
           count(DISTINCT order_id) AS delivered_orders
    FROM published.fct_order_items WHERE order_status = 'delivered' GROUP BY 1
), monthly AS (
    SELECT date_trunc('month', purchase_date)::date AS purchase_month,
           sum(order_count) AS all_status_orders, sum(revenue_brl) AS delivered_item_value_brl
    FROM published.fct_daily_sales GROUP BY 1
)
SELECT m.*, coalesce(d.delivered_orders, 0) AS delivered_orders,
       round(m.delivered_item_value_brl / nullif(d.delivered_orders, 0), 2) AS item_value_per_delivered_order_brl
FROM monthly m LEFT JOIN delivered d USING (purchase_month) ORDER BY purchase_month;
