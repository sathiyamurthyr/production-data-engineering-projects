-- Query Execution Plans and Optimization Analysis
-- Business Use Case: Understanding and optimizing query performance

-- =============================================================================
-- EXPLAIN ANALYZE - Understand query execution
-- =============================================================================

-- Basic EXPLAIN without execution
EXPLAIN 
SELECT c.first_name, o.total_amount
FROM raw_customers c
JOIN raw_orders o ON c.customer_id = o.customer_id
WHERE o.order_date >= '2024-01-01';

-- EXPLAIN ANALYZE with actual execution (for testing)
-- EXPLAIN ANALYZE
-- SELECT c.first_name, SUM(o.total_amount) as total_spent
-- FROM raw_customers c
-- LEFT JOIN raw_orders o ON c.customer_id = o.customer_id
-- GROUP BY c.customer_id, c.first_name;

-- =============================================================================
-- 07 Index Selection - Create indexes for performance
-- =============================================================================

-- Index on join column
CREATE INDEX idx_orders_customer_id ON raw_orders(customer_id);

-- Index on filtered column
CREATE INDEX idx_orders_date ON raw_orders(order_date);

-- Composite index for multi-column queries
CREATE INDEX idx_orders_customer_date ON raw_orders(customer_id, order_date);

-- Covering index (index includes all columns needed)
CREATE INDEX idx_orders_covering ON raw_orders(customer_id, order_date, total_amount)
INCLUDE (order_id, order_status);

-- Partial index for filtered queries
CREATE INDEX idx_active_customers ON raw_customers(customer_id)
WHERE status = 'active';

-- =============================================================================
-- 27 Statistics - Update for optimizer
-- =============================================================================

-- Update table statistics
ANALYZE raw_customers;
ANALYZE raw_orders;

-- Show table statistics
SELECT 
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats
WHERE tablename IN ('raw_customers', 'raw_orders');

-- =============================================================================
-- 21 Partition Pruning - Optimize large tables
-- =============================================================================

-- Create partitioned table by date range
CREATE TABLE fact_sales_partitioned (
    sale_id BIGINT,
    customer_id INTEGER,
    order_date DATE,
    amount DECIMAL(10,2)
) PARTITION BY RANGE (order_date);

-- Create partitions
CREATE TABLE fact_sales_2024_q1 PARTITION OF fact_sales_partitioned
FOR VALUES FROM ('2024-01-01') TO ('2024-04-01');

CREATE TABLE fact_sales_2024_q2 PARTITION OF fact_sales_partitioned
FOR VALUES FROM ('2024-04-01') TO ('2024-07-01');

-- Query with partition pruning
-- This will only scan relevant partitions
EXPLAIN 
SELECT SUM(amount) 
FROM fact_sales_partitioned 
WHERE order_date >= '2024-03-01' AND order_date < '2024-04-01';

-- =============================================================================
-- 15 Join Optimization - Different join strategies
-- =============================================================================

-- Hash Join (for large equality joins)
-- The optimizer chooses this when joining large tables on equality
EXPLAIN 
SELECT COUNT(*) 
FROM raw_customers c
JOIN raw_orders o ON c.customer_id = o.customer_id;

-- Merge Join (requires sorted input)
-- Create index to enable merge join
CREATE INDEX idx_orders_customer_sorted ON raw_orders(customer_id);
CREATE INDEX idx_customers_id_sorted ON raw_customers(customer_id);

-- =============================================================================
-- 24 Materialized Views - Pre-computed aggregations
-- =============================================================================

-- Create materialized view for daily sales
CREATE MATERIALIZED VIEW mv_daily_sales AS
SELECT 
    order_date,
    COUNT(*) as order_count,
    SUM(total_amount) as daily_revenue,
    AVG(total_amount) as avg_order_value
FROM raw_orders
GROUP BY order_date;

-- Refresh materialized view
REFRESH MATERIALIZED VIEW mv_daily_sales;

-- Query materialized view (fast - no aggregation needed)
SELECT * FROM mv_daily_sales ORDER BY order_date DESC LIMIT 7;