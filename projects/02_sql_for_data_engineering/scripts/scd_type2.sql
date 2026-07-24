-- Slowly Changing Dimension Type 2 Implementation
-- Business Use Case: Track complete history of customer changes
-- When a customer attribute changes, create a new record with new dates

-- Step 1: Expire current records where data has changed
UPDATE dim_customer 
SET 
    is_current = FALSE,
    expiry_date = CURRENT_DATE - INTERVAL '1 day'
WHERE 
    is_current = TRUE
    AND EXISTS (
        SELECT 1 
        FROM raw_customers rc 
        WHERE rc.customer_id = dim_customer.customer_id
        AND (
            COALESCE(dim_customer.email, '') != COALESCE(rc.email, '') OR
            COALESCE(dim_customer.city, '') != COALESCE(rc.city, '') OR
            COALESCE(dim_customer.country, '') != COALESCE(rc.country, '')
        )
    );

-- Step 2: Insert new records for changed customers
INSERT INTO dim_customer (
    customer_id, first_name, last_name, email, city, state, country, 
    signup_date, status, effective_date, expiry_date, is_current
)
SELECT 
    rc.customer_id,
    rc.first_name,
    rc.last_name,
    rc.email,
    rc.city,
    rc.state,
    rc.country,
    rc.signup_date,
    rc.status,
    CURRENT_DATE,
    DATE '9999-12-31',
    TRUE
FROM raw_customers rc
WHERE EXISTS (
    SELECT 1 
    FROM dim_customer dc 
    WHERE dc.customer_id = rc.customer_id 
    AND dc.is_current = FALSE
    AND (
        COALESCE(dc.email, '') != COALESCE(rc.email, '') OR
        COALESCE(dc.city, '') != COALESCE(rc.city, '')
    )
) OR rc.customer_id NOT IN (SELECT customer_id FROM dim_customer);

-- Query to get current customer view (use this for reporting)
CREATE OR REPLACE VIEW v_current_customers AS
SELECT 
    customer_sk,
    customer_id,
    first_name,
    last_name,
    email,
    city,
    state,
    country,
    signup_date,
    status
FROM dim_customer
WHERE is_current = TRUE;