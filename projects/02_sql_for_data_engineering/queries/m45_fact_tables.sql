/*
================================================================================
MODULE 45: Fact Table Types (Transaction, Periodic Snapshot, Accumulating)
================================================================================
1. EXPLANATION:
Fact tables store numerical metrics (revenue, quantity) linked to surrogate dimension keys.
*/

SELECT 
    customer_key,
    product_key,
    quantity,
    net_amount
FROM fact_sales;
