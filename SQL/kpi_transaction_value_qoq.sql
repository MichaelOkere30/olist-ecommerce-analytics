CREATE OR REPLACE VIEW kpi_transaction_value_qoq AS
WITH quarterly_value AS (
    SELECT
        d.year,
        d.quarter,
        d.year_quarter,
        SUM(f.price + f.freight_value) AS total_transaction_value,
        COUNT(DISTINCT f.order_id)     AS total_orders,
        ROUND(SUM(f.price + f.freight_value) / NULLIF(COUNT(DISTINCT f.order_id), 0), 2) AS aov
    FROM fact_order_items f
    INNER JOIN dim_date d
        ON TO_CHAR(f.order_purchase_timestamp, 'YYYYMMDD')::integer = d.date_key
    WHERE f.order_status NOT IN ('canceled', 'unavailable')
    GROUP BY d.year, d.quarter, d.year_quarter
)
SELECT
    year,
    quarter,
    year_quarter,
    total_transaction_value,
    total_orders,
    aov,
    LAG(total_transaction_value) OVER (ORDER BY year, quarter) AS previous_quarter_value,
    ROUND(
        (total_transaction_value - LAG(total_transaction_value) OVER (ORDER BY year, quarter)) * 100.0
        / NULLIF(LAG(total_transaction_value) OVER (ORDER BY year, quarter), 0)
    , 2) AS transaction_value_growth_pct
FROM quarterly_value
ORDER BY year, quarter;