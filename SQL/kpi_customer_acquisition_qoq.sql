-- ----------------------------------------------------------------------------
-- 1. CUSTOMER ACQUISITION QoQ  (fixed: group by customer_unique_id)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW kpi_customer_acquisition_qoq AS
WITH customer_first_order AS (
    -- First order date of every real customer (deduped via customer_unique_id)
    SELECT
        c.customer_unique_id,
        MIN(f.order_purchase_timestamp)::date AS first_order_date
    FROM fact_order_items f
    INNER JOIN dim_customer c
        ON f.customer_id = c.customer_id
    WHERE f.order_status NOT IN ('canceled', 'unavailable')
    GROUP BY c.customer_unique_id
),
quarterly_new_customers AS (
    SELECT
        d.year,
        d.quarter,
        d.year_quarter,
        COUNT(DISTINCT cfo.customer_unique_id) AS new_customers
    FROM customer_first_order cfo
    INNER JOIN dim_date d
        ON cfo.first_order_date = d.full_date
    GROUP BY d.year, d.quarter, d.year_quarter
)
SELECT
    year,
    quarter,
    year_quarter,
    new_customers,
    LAG(new_customers) OVER (ORDER BY year, quarter) AS previous_quarter_new_customers,
    ROUND(
        (new_customers - LAG(new_customers) OVER (ORDER BY year, quarter)) * 100.0
        / NULLIF(LAG(new_customers) OVER (ORDER BY year, quarter), 0)
    , 2) AS acquisition_growth_pct
FROM quarterly_new_customers
ORDER BY year, quarter;
