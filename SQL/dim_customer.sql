CREATE OR REPLACE VIEW dim_customer AS
SELECT
    customer_id,
    customer_unique_id,                    -- better for true unique customers
    customer_zip_code_prefix,
    customer_city,
    customer_state,
    
    -- You can add more later (first order date, total orders, etc.)
    -- but keep it simple for now
    customer_city || ', ' || customer_state AS customer_location
FROM customers;