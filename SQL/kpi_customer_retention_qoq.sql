-- ----------------------------------------------------------------------------
-- 2. CUSTOMER RETENTION QoQ  (fixed: group by customer_unique_id)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW kpi_customer_retention_qoq AS
WITH customer_quarters AS (
    -- All distinct real customers active in each quarter
    SELECT DISTINCT
        c.customer_unique_id,
        d.year,
        d.quarter,
        d.year_quarter
    FROM fact_order_items f
    INNER JOIN dim_customer c
        ON f.customer_id = c.customer_id
    INNER JOIN dim_date d
        ON TO_CHAR(f.order_purchase_timestamp, 'YYYYMMDD')::integer = d.date_key
    WHERE f.order_status NOT IN ('canceled', 'unavailable')
),
quarterly_active AS (
    SELECT
        year,
        quarter,
        year_quarter,
        COUNT(DISTINCT customer_unique_id) AS active_customers
    FROM customer_quarters
    GROUP BY year, quarter, year_quarter
),
retained AS (
    SELECT
        curr.year,
        curr.quarter,
        curr.year_quarter,
        COUNT(DISTINCT curr.customer_unique_id) AS retained_customers
    FROM customer_quarters curr
    INNER JOIN customer_quarters prev
        ON curr.customer_unique_id = prev.customer_unique_id
       AND (
            (curr.year = prev.year AND curr.quarter = prev.quarter + 1)
            OR
            (curr.year = prev.year + 1 AND curr.quarter = 1 AND prev.quarter = 4)
           )
    GROUP BY curr.year, curr.quarter, curr.year_quarter
)
SELECT
    qa.year,
    qa.quarter,
    qa.year_quarter,
    qa.active_customers,
    COALESCE(r.retained_customers, 0) AS retained_customers,
    ROUND(
        COALESCE(r.retained_customers, 0) * 100.0
        / NULLIF(LAG(qa.active_customers) OVER (ORDER BY qa.year, qa.quarter), 0)
    , 2) AS retention_rate_pct
FROM quarterly_active qa
LEFT JOIN retained r
    ON qa.year = r.year AND qa.quarter = r.quarter
ORDER BY qa.year, qa.quarter;
