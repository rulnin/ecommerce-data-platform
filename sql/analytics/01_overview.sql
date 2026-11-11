-- Q1: What is the snapshot's order volume and delivered-item sales proxy?
SELECT min(purchase_date) AS first_purchase_date, max(purchase_date) AS last_purchase_date,
       sum(order_count) AS orders, sum(item_count) AS items, sum(payment_count) AS payment_entries,
       sum(item_value_brl) AS all_status_item_value_brl,
       sum(revenue_brl) AS delivered_item_value_brl,
       sum(freight_value_brl) AS freight_brl, sum(payment_value_brl) AS payment_value_brl
FROM published.fct_daily_sales;
