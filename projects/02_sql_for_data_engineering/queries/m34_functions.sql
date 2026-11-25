/*
================================================================================
MODULE 34: User-Defined Functions (UDFs)
================================================================================
1. EXPLANATION:
UDFs encapsulate reusable mathematical or formatting logic.
*/

SELECT 
    net_amount,
    (net_amount * 0.08) AS estimated_tax
FROM fact_sales;
