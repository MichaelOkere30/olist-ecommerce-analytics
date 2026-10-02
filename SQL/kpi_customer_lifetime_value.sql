DROP VIEW IF EXISTS kpi_customer_lifetime_value;

CREATE VIEW kpi_customer_lifetime_value AS
WITH customer_metrics AS (
    SELECT
        c.customer_unique_id,
        COUNT(DISTINCT f.order_id)                AS total_orders,
        SUM(f.price + f.freight_value)            AS total_revenue,
        MIN(f.order_purchase_timestamp)::date     AS first_order_date,
        MAX(f.order_purchase_timestamp)::date     AS last_order_date,
        (MAX(f.order_purchase_timestamp)::date -
         MIN(f.order_purchase_timestamp)::date)   AS lifespan_days
    FROM fact_order_items f
    INNER JOIN dim_customer c
        ON f.customer_id = c.customer_id
    WHERE f.order_status NOT IN ('canceled', 'unavailable')
    GROUP BY c.customer_unique_id
)
SELECT
    customer_unique_id,
    total_orders,
    ROUND(total_revenue, 2)                                       AS total_revenue,
    ROUND(total_revenue / NULLIF(total_orders, 0), 2)             AS aov,
    ROUND(total_orders / NULLIF(lifespan_days / 365.0, 0), 2)     AS purchase_frequency_per_year,
    ROUND(lifespan_days / 365.0, 2)                               AS lifespan_years,
    ROUND(total_revenue, 2)                                       AS customer_lifetime_value,
    (total_orders > 1)                                            AS is_repeat_customer,
    first_order_date,
    last_order_date
FROM customer_metrics
ORDER BY customer_lifetime_value DESC;