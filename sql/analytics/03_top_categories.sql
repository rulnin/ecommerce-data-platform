-- Q3: Which ten categories contribute most delivered item value?
WITH categories AS (
    SELECT coalesce(p.category_name_english, p.category_name, 'Unknown') AS category,
           count(*) AS delivered_items, count(DISTINCT i.order_id) AS delivered_orders,
           sum(i.item_price_brl) AS delivered_item_value_brl
    FROM published.fct_order_items i JOIN published.dim_product p USING (product_id)
    WHERE i.order_status = 'delivered' GROUP BY 1
)
SELECT *, round(100 * delivered_item_value_brl / nullif(sum(delivered_item_value_brl) OVER (), 0), 2) AS share_pct
FROM categories ORDER BY delivered_item_value_brl DESC, category LIMIT 10;
