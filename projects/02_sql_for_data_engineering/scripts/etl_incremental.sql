-- Incremental ETL Pattern for Data Engineering
-- Business Use Case: Loading only changed data for efficiency

-- Method 1: Using a watermark column (last_modified)
INSERT INTO dim_customer (
    customer_id, first_name, last_name, email, city, state, country, signup_date, status
)
SELECT 
    customer_id, first_name, last_name, email, city, state, country, signup_date, status
FROM raw_customers
WHERE updated_at > (SELECT MAX(effective_date) FROM dim_customer);

-- Method 2: Using a change tracking table
INSERT INTO fact_sales (
    customer_sk, product_sk, order_date_sk, order_id, quantity, unit_price, total_amount
)
SELECT 
    c.customer_sk,
    p.product_sk,
    d.date_sk,
    r.order_id,
    r.quantity,
    r.unit_price,
    r.total_amount
FROM raw_orders r
JOIN change_tracking ct ON r.order_id = ct.order_id
JOIN dim_customer c ON r.customer_id = c.customer_id AND c.is_current = TRUE
JOIN dim_product p ON r.product_id = p.product_id AND p.is_current = TRUE
JOIN dim_date d ON r.order_date = d.date_value
WHERE ct.change_type IN ('INSERT', 'UPDATE');

-- Method 3: Merge/Upsert pattern (PostgreSQL 15+)
MERGE INTO dim_customer AS target
USING raw_customers AS source
ON target.customer_id = source.customer_id
WHEN MATCHED AND target.email != source.email THEN
    UPDATE SET 
        first_name = source.first_name,
        last_name = source.last_name,
        email = source.email,
        city = source.city,
        is_current = FALSE,
        expiry_date = CURRENT_DATE
WHEN NOT MATCHED THEN
    INSERT (customer_id, first_name, last_name, email, city, state, country, signup_date, status)
    VALUES (source.customer_id, source.first_name, source.last_name, source.email, 
            source.city, source.state, source.country, source.signup_date, source.status);