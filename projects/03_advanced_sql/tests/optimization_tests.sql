-- Optimization Tests for Advanced SQL
-- Business Use Case: Validate query performance improvements

-- =============================================================================
-- Test 1: Verify index usage
-- Expected: Index scan instead of sequential scan
-- =============================================================================
EXPLAIN 
SELECT * FROM raw_orders WHERE order_date = '2024-01-15';

-- =============================================================================
-- Test 2: Verify partition pruning
-- Expected: Only scan relevant partition
-- =============================================================================
EXPLAIN 
SELECT SUM(total_amount) FROM raw_orders 
WHERE order_date >= '2024-01-01' AND order_date < '2024-02-01';

-- =============================================================================
-- Test 3: Verify join strategy
-- Expected: Hash join for large tables
-- =============================================================================
EXPLAIN 
SELECT COUNT(*) FROM raw_customers c JOIN raw_orders o ON c.customer_id = o.customer_id;

-- =============================================================================
-- Test 4: Query with CTE optimization
-- Expected: Materialized CTE for repeated use
-- =============================================================================
EXPLAIN 
WITH RECURSIVE date_range AS (
    SELECT '2024-01-01'::DATE as dt
    UNION ALL
    SELECT dt + INTERVAL '1 day' FROM date_range WHERE dt < '2024-01-31'
)
SELECT d.dt, COUNT(o.order_id) as order_count
FROM date_range d
LEFT JOIN raw_orders o ON d.dt = o.order_date
GROUP BY d.dt;

-- =============================================================================
-- Test 5: Window function performance
-- Expected: Efficient window processing
-- =============================================================================
EXPLAIN 
SELECT 
    customer_id,
    total_amount,
    ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY total_amount DESC)
FROM raw_orders;

-- =============================================================================
-- Test 6: Materialized view refresh
-- Expected: Fast query on MV
-- =============================================================================
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_sales;
-- EXPLAIN ANALYZE SELECT * FROM mv_daily_sales LIMIT 10;

-- =============================================================================
-- Performance Validation Queries
-- =============================================================================
-- Check query execution time threshold
SELECT 
    query, 
    mean_time 
FROM pg_stat_statements 
WHERE mean_time > 1000  -- > 1 second
ORDER BY mean_time DESC;