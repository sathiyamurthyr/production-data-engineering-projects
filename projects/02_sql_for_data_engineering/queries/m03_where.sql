/*
================================================================================
MODULE 03: WHERE Clause & Predicate Filtering
================================================================================
1. EXPLANATION:
WHERE filters rows BEFORE aggregation occurs. Utilize indexed columns to enable index scan / partition pruning.
*/

SELECT 
    transaction_id,
    customer_key,
    net_amount,
    status
FROM fact_sales
WHERE status = 'COMPLETED' AND net_amount > 1000.00;
