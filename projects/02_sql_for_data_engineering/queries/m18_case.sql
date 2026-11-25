/*
================================================================================
MODULE 18: CASE Statement & Conditional Categorization
================================================================================
1. EXPLANATION:
CASE expressions implement if-else branching logic inside SQL queries.
*/

SELECT 
    transaction_id,
    net_amount,
    CASE 
        WHEN net_amount >= 2000.00 THEN 'HIGH_VALUE'
        WHEN net_amount >= 1000.00 THEN 'MEDIUM_VALUE'
        ELSE 'LOW_VALUE'
    END AS transaction_tier
FROM fact_sales;
