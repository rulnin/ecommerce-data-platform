-- Q5: How are recorded tender amounts distributed by payment type (all statuses)?
SELECT payment_type, count(*) AS payment_entries, sum(payment_value_brl) AS payment_value_brl,
       round(100 * sum(payment_value_brl) / nullif(sum(sum(payment_value_brl)) OVER (), 0), 2) AS value_share_pct
FROM published.fct_payments GROUP BY payment_type ORDER BY payment_value_brl DESC, payment_type;
