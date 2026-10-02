CREATE OR REPLACE VIEW fact_order_items AS
SELECT
    oi.order_id,
    oi.order_item_id,
    o.customer_id,
    oi.product_id,
    oi.seller_id,
    
    -- Date keys for easy joining to DimDate
    TO_CHAR(o.order_purchase_timestamp, 'YYYYMMDD')::integer AS order_date_key,
    o.order_purchase_timestamp,
    o.order_approved_at,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,
    
    -- Measures
    oi.price,
    oi.freight_value,
    (oi.price + oi.freight_value)                     AS total_item_value,   -- useful for AOV
    op.payment_value,                                 -- total payment for the order (can be repeated)
    
    -- Status
    o.order_status,
    
    -- Delivery metrics (you already calculated these)
    o.delivery_time_days,
    o.target_delivery_time_days

FROM order_items oi
INNER JOIN orders o 
    ON oi.order_id = o.order_id
LEFT JOIN order_payment op 
    ON oi.order_id = op.order_id 
   AND op.payment_sequential = 1;   -- take the first payment record