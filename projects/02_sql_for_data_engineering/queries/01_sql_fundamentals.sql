-- SQL Fundamentals for Data Engineering
-- Business Use Case: Foundation queries for ETL pipelines

-- =============================================================================
-- 02 SELECT - Data Extraction
-- =============================================================================
-- Select all columns
SELECT * FROM raw_customers;

-- Select specific columns
SELECT customer_id, first_name, last_name, email 
FROM raw_customers;

-- Select with expressions
SELECT 
    customer_id,
    first_name || ' ' || last_name as full_name,
    UPPER(country) as country_upper,
    CURRENT_TIMESTAMP as extraction_timestamp
FROM raw_customers;

-- =============================================================================
-- 03 WHERE - Data Filtering
-- =============================================================================
-- Equality and comparison
SELECT * FROM raw_customers 
WHERE status = 'active' AND age >= 18;

-- IN operator for multiple values
SELECT * FROM raw_orders 
WHERE order_status IN ('completed', 'pending');

-- LIKE for pattern matching
SELECT * FROM raw_customers 
WHERE email LIKE '%@email.com';

-- BETWEEN for range
SELECT * FROM raw_orders 
WHERE order_date BETWEEN '2024-01-01' AND '2024-01-31';

-- IS NULL for missing values
SELECT * FROM raw_customers 
WHERE phone IS NULL;

-- =============================================================================
-- 04 ORDER BY - Sorting Results
-- =============================================================================
-- Single column sort
SELECT * FROM raw_customers 
ORDER BY signup_date DESC;

-- Multiple column sort
SELECT * FROM raw_orders 
ORDER BY customer_id ASC, total_amount DESC;

-- =============================================================================
-- 05 LIMIT - Pagination
-- =============================================================================
-- Top N records
SELECT * FROM raw_orders 
ORDER BY total_amount DESC 
LIMIT 10;

-- Offset for pagination
SELECT * FROM raw_customers 
ORDER BY customer_id 
LIMIT 10 OFFSET 20;

-- =============================================================================
-- 06 DISTINCT - Deduplication
-- =============================================================================
-- Get unique countries
SELECT DISTINCT country FROM raw_customers;

-- Count unique customers per country
SELECT 
    country, 
    COUNT(DISTINCT customer_id) as unique_customers
FROM raw_customers 
GROUP BY country;

-- =============================================================================
-- 07 Aliases - Readable Queries
-- =============================================================================
-- Column aliases
SELECT 
    customer_id as id,
    first_name as fname,
    last_name as lname
FROM raw_customers;

-- Table aliases
SELECT 
    c.customer_id,
    o.order_id,
    o.total_amount
FROM raw_customers c
JOIN raw_orders o ON c.customer_id = o.customer_id;

-- =============================================================================
-- 08 Aggregate Functions - Metrics
-- =============================================================================
-- Count, Sum, Avg
SELECT 
    COUNT(*) as total_records,
    COUNT(order_id) as completed_orders,
    SUM(total_amount) as total_revenue,
    AVG(total_amount) as avg_order_value,
    MIN(total_amount) as min_order,
    MAX(total_amount) as max_order
FROM raw_orders;

-- =============================================================================
-- 09 GROUP BY - Aggregation
-- =============================================================================
-- Group by single column
SELECT 
    country,
    COUNT(*) as customer_count,
    AVG(age) as avg_age
FROM raw_customers 
GROUP BY country;

-- Group by multiple columns
SELECT 
    YEAR(signup_date) as signup_year,
    MONTH(signup_date) as signup_month,
    COUNT(*) as new_customers
FROM raw_customers 
GROUP BY YEAR(signup_date), MONTH(signup_date)
ORDER BY signup_year, signup_month;

-- =============================================================================
-- 10 HAVING - Filtered Aggregation
-- =============================================================================
SELECT 
    country,
    COUNT(*) as customer_count
FROM raw_customers 
GROUP BY country 
HAVING COUNT(*) > 1;

-- =============================================================================
-- 11 JOINs - Data Integration
-- =============================================================================
-- INNER JOIN - Only matching records
SELECT 
    c.first_name,
    o.order_id,
    o.total_amount
FROM raw_customers c
INNER JOIN raw_orders o ON c.customer_id = o.customer_id;

-- LEFT JOIN - All customers with optional orders
SELECT 
    c.first_name,
    COUNT(o.order_id) as order_count,
    COALESCE(SUM(o.total_amount), 0) as total_spent
FROM raw_customers c
LEFT JOIN raw_orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.first_name;

-- RIGHT JOIN - All orders with customer details
SELECT 
    o.order_id,
    c.first_name,
    o.total_amount
FROM raw_customers c
RIGHT JOIN raw_orders o ON c.customer_id = o.customer_id;

-- FULL OUTER JOIN - Everything
SELECT 
    COALESCE(c.first_name, 'Unknown') as customer,
    COALESCE(o.order_id, 0) as order_id
FROM raw_customers c
FULL OUTER JOIN raw_orders o ON c.customer_id = o.customer_id;

-- =============================================================================
-- 12 Self Join - Hierarchical Data
-- =============================================================================
-- Find customers in same country
SELECT 
    c1.first_name as customer1,
    c2.first_name as customer2,
    c1.country
FROM raw_customers c1
JOIN raw_customers c2 ON c1.country = c2.country 
    AND c1.customer_id < c2.customer_id;

-- =============================================================================
-- 13 Cross Join - Cartesian Product
-- =============================================================================
-- Generate all combinations (use carefully!)
SELECT 
    c.first_name,
    p.product_name
FROM raw_customers c
CROSS JOIN raw_products p
LIMIT 5;

-- =============================================================================
-- 14 UNION - Combine Results
-- =============================================================================
-- UNION (removes duplicates)
SELECT email FROM raw_customers
UNION
SELECT email FROM raw_vendors;

-- UNION ALL (keeps duplicates - faster)
SELECT email, 'customer' as source FROM raw_customers
UNION ALL
SELECT email, 'vendor' as source FROM raw_vendors;

-- =============================================================================
-- 15 INTERSECT - Common Records
-- =============================================================================
SELECT country FROM raw_customers
INTERSECT
SELECT country FROM raw_vendors;

-- =============================================================================
-- 16 EXCEPT - Difference
-- =============================================================================
SELECT country FROM raw_customers
EXCEPT
SELECT country FROM raw_vendors;

-- =============================================================================
-- 17 CASE - Conditional Logic
-- =============================================================================
SELECT 
    customer_id,
    total_amount,
    CASE 
        WHEN total_amount > 200 THEN 'High'
        WHEN total_amount > 100 THEN 'Medium'
        ELSE 'Low'
    END as order_tier
FROM raw_orders;

-- =============================================================================
-- 18 NULL Handling - Missing Data
-- =============================================================================
SELECT 
    customer_id,
    phone,
    COALESCE(phone, 'Not provided') as phone_clean
FROM raw_customers;

-- =============================================================================
-- 19 COALESCE - Default Values
-- =============================================================================
SELECT 
    customer_id,
    COALESCE(phone, email, 'No contact') as contact_info
FROM raw_customers;

-- =============================================================================
-- 20 CAST - Type Conversion
-- =============================================================================
SELECT 
    CAST('2024-01-15' AS DATE) as order_date,
    CAST(total_amount AS INTEGER) as rounded_amount,
    CAST(customer_id AS VARCHAR) as customer_id_str
FROM raw_orders;