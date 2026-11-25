/*
================================================================================
MODULE 38: Query Performance Tuning & Pruning
================================================================================
1. EXPLANATION:
Query optimization avoids Cartesian joins, uses selective WHERE filters, and minimizes SELECT columns.
*/

SELECT s.transaction_id, s.net_amount
FROM fact_sales s
WHERE s.sale_date >= '2026-07-01' AND s.status = 'COMPLETED';
