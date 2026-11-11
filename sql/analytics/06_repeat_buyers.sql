-- Q6: What fraction of people have more than one delivered order in this snapshot?
WITH delivered_orders AS (
    SELECT DISTINCT order_id, customer_id FROM published.fct_order_items WHERE order_status = 'delivered'
), people AS (
    SELECT c.customer_unique_id, count(*) AS delivered_orders
    FROM delivered_orders o JOIN published.dim_customer c USING (customer_id)
    GROUP BY c.customer_unique_id
)
SELECT count(*) AS delivered_buyers, sum(delivered_orders) AS delivered_orders,
       count(*) FILTER (WHERE delivered_orders > 1) AS repeat_buyers,
       round(100.0 * count(*) FILTER (WHERE delivered_orders > 1) / nullif(count(*), 0), 2) AS repeat_buyer_pct
FROM people;
