-- SQL Validation Tests for Data Quality
-- Business Use Case: Validate data integrity in ETL pipelines

-- Test 1: Primary Key Validation (no duplicates)
SELECT 
    customer_id,
    COUNT(*) as duplicate_count
FROM raw_customers
GROUP BY customer_id
HAVING COUNT(*) > 1;

-- Test 2: Foreign Key Validation (orphaned records)
SELECT 
    o.order_id,
    o.customer_id
FROM raw_orders o
LEFT JOIN raw_customers c ON o.customer_id = c.customer_id
WHERE c.customer_id IS NULL;

-- Test 3: NULL Checks (required fields)
SELECT 
    COUNT(*) as null_email_count
FROM raw_customers
WHERE email IS NULL OR email = '';

-- Test 4: Data Range Validation
SELECT 
    COUNT(*) as invalid_age_count
FROM raw_customers
WHERE age < 0 OR age > 120;

-- Test 5: Duplicate Detection (email uniqueness)
SELECT 
    email,
    COUNT(*) as duplicate_count
FROM raw_customers
GROUP BY email
HAVING COUNT(*) > 1;

-- Test 6: Referential Integrity (country validation)
SELECT 
    country,
    COUNT(*) as invalid_country_count
FROM raw_customers
WHERE country NOT IN ('USA', 'Canada', 'UK', 'Australia', 'Germany', 'France')
GROUP BY country;

-- Test 7: Date Validation
SELECT 
    COUNT(*) as future_date_count
FROM raw_orders
WHERE order_date > CURRENT_DATE;

-- Test 8: Business Rule Validation (order amount)
SELECT 
    COUNT(*) as invalid_amount_count
FROM raw_orders
WHERE total_amount <= 0;

-- Test 9: Consistency Check (status values)
SELECT 
    status,
    COUNT(*) as status_count
FROM raw_customers
WHERE status NOT IN ('active', 'inactive', 'suspended');

-- Test 10: Row Count Validation (between source and target)
WITH source_count AS (
    SELECT COUNT(*) as src_cnt FROM raw_customers
),
target_count AS (
    SELECT COUNT(*) as tgt_cnt FROM dim_customer
)
SELECT 
    src_cnt,
    tgt_cnt,
    ABS(src_cnt - tgt_cnt) as difference
FROM source_count, target_count;

-- Summary Report
SELECT 
    (SELECT COUNT(*) FROM raw_customers) as total_customers,
    (SELECT COUNT(*) FROM raw_orders) as total_orders,
    (SELECT COUNT(*) FROM raw_products) as total_products,
    (SELECT COUNT(*) FROM raw_customers WHERE status = 'active') as active_customers;