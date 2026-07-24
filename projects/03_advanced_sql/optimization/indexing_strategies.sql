-- Production Indexing Strategies for Enterprise Data Warehouses
-- Business Use Case: Optimize query performance for billion-row tables

-- =============================================================================
-- B-Tree Index - Default for most queries
-- =============================================================================
-- Use for range queries, ORDER BY, GROUP BY
CREATE INDEX idx_orders_date_btree ON raw_orders(order_date);

-- =============================================================================
-- Composite Index - Multi-column optimization
-- =============================================================================
-- Order matters! Most selective column first
CREATE INDEX idx_orders_composite ON raw_orders(customer_id, order_status, order_date);

-- =============================================================================
-- Covering Index - Index-only scans
-- =============================================================================
-- Include all columns needed to avoid table lookup
CREATE INDEX idx_orders_covering ON raw_orders(customer_id, order_date, total_amount)
INCLUDE (order_id, order_status, payment_method);

-- =============================================================================
-- Partial Index - Index subset of data
-- =============================================================================
-- Reduce index size for filtered queries
CREATE INDEX idx_orders_completed ON raw_orders(order_date, total_amount)
WHERE order_status = 'completed';

-- =============================================================================
-- BRIN Index - Large sorted tables (billion rows)
-- =============================================================================
-- Block Range Index - very small, good for time-series
CREATE INDEX idx_large_table_brin ON large_events USING BRIN(event_timestamp);

-- =============================================================================
-- Expression Index - Computed columns
-- =============================================================================
-- For queries with functions
CREATE INDEX idx_lower_email ON raw_customers(LOWER(email));

-- =============================================================================
-- Unique Index - Enforce constraints + optimize
-- =============================================================================
CREATE UNIQUE INDEX idx_unique_email ON raw_customers(email);

-- =============================================================================
-- Index Maintenance
-- =============================================================================
-- Rebuild fragmented indexes
REINDEX INDEX idx_orders_date_btree;

-- Drop unused indexes
-- SELECT * FROM pg_stat_user_indexes WHERE idx_tup_read = 0;

-- =============================================================================
-- Index Usage Monitoring
-- =============================================================================
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_tup_read,
    idx_tup_fetch,
    idx_scan
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;