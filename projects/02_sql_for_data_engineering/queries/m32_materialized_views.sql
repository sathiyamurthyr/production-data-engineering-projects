/*
================================================================================
MODULE 32: Materialized Views & Pre-Aggregated Caching
================================================================================
1. EXPLANATION:
Materialized Views physically persist query results to disk to accelerate dashboard performance.
*/

-- Conceptual Materialized View Query Pattern
SELECT 
    p.category,
    SUM(s.net_amount) AS category_revenue
FROM fact_sales s
JOIN dim_products p ON s.product_key = p.product_key
GROUP BY p.category;
