-- Q7: Which sellers contribute most delivered item value? Stable anonymous ranks.
WITH sellers AS (
    SELECT s.seller_id, s.state AS seller_state, count(*) AS delivered_items,
           count(DISTINCT i.order_id) AS delivered_orders, sum(i.item_price_brl) AS delivered_item_value_brl
    FROM published.fct_order_items i JOIN published.dim_seller s USING (seller_id)
    WHERE i.order_status = 'delivered' GROUP BY s.seller_id, s.state
)
SELECT row_number() OVER (ORDER BY delivered_item_value_brl DESC, seller_id) AS seller_rank,
       seller_state, delivered_items, delivered_orders, delivered_item_value_brl,
       round(100 * delivered_item_value_brl / nullif(sum(delivered_item_value_brl) OVER (), 0), 2) AS share_pct
FROM sellers ORDER BY delivered_item_value_brl DESC, seller_id LIMIT 10;
