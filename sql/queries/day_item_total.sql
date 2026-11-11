-- Independent item-only total for Black Friday; never join payment rows here.
WITH selected AS MATERIALIZED (
    SELECT data->>'order_id' AS order_id FROM raw.orders
    WHERE data->>'order_purchase_timestamp' >= '2017-11-24 00:00:00'
      AND data->>'order_purchase_timestamp' < '2017-11-25 00:00:00'
)
SELECT count(*) AS item_count, sum((i.data->>'price')::numeric) AS item_value_brl
FROM raw.order_items i JOIN selected s ON i.data->>'order_id' = s.order_id;
