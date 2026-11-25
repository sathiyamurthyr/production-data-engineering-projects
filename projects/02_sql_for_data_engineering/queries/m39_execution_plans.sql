/*
================================================================================
MODULE 39: EXPLAIN Query Execution Plans
================================================================================
1. EXPLANATION:
`EXPLAIN QUERY PLAN` reveals the internal execution strategy (Index Scan vs Full Table Scan).
*/

EXPLAIN QUERY PLAN 
SELECT s.transaction_id, c.email
FROM fact_sales s
JOIN dim_customers c ON s.customer_key = c.customer_key
WHERE s.status = 'COMPLETED';
