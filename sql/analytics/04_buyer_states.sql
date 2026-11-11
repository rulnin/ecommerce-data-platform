-- Q4: Where are the customers generating delivered item value?
SELECT c.state AS buyer_state, count(DISTINCT i.order_id) AS delivered_orders,
       sum(i.item_price_brl) AS delivered_item_value_brl
FROM published.fct_order_items i JOIN published.dim_customer c USING (customer_id)
WHERE i.order_status = 'delivered'
GROUP BY c.state ORDER BY delivered_item_value_brl DESC, c.state;
