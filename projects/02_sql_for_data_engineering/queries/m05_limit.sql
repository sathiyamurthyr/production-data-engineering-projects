/*
================================================================================
MODULE 05: LIMIT & TOP Clause for Sampling
================================================================================
1. EXPLANATION:
LIMIT restricts output row count. Useful for data profiling and debugging micro-batches.
*/

SELECT 
    transaction_id,
    sale_date,
    net_amount
FROM fact_sales
ORDER BY sale_date DESC
LIMIT 5;
