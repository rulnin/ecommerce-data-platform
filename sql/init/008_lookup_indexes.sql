-- Expression indexes for selective historical order/item investigation.
-- Text dates are compared in the canonical Olist YYYY-MM-DD HH:MM:SS format.
-- Keep predicates identical to these expressions; timestamp casts do not use them.
CREATE INDEX IF NOT EXISTS orders_purchase_text_idx
    ON raw.orders ((data->>'order_purchase_timestamp'));
CREATE INDEX IF NOT EXISTS order_items_order_id_idx
    ON raw.order_items ((data->>'order_id'));
