/*
================================================================================
MODULE 07: Column & Table Aliasing
================================================================================
1. EXPLANATION:
Aliases (`AS`) rename output columns and shorten table references in complex multi-table joins.
*/

SELECT 
    s.transaction_id AS txn_reference,
    s.net_amount AS total_revenue_usd
FROM fact_sales AS s;
