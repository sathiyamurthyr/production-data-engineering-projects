/*
================================================================================
MODULE 50: Data Quality Validation Rules
================================================================================
1. EXPLANATION:
Data quality validation checks for nulls, negative amounts, and invalid statuses before target loading.
*/

SELECT 
    COUNT(*) AS total_records,
    SUM(CASE WHEN net_amount < 0 THEN 1 ELSE 0 END) AS invalid_negative_amounts,
    SUM(CASE WHEN customer_key IS NULL THEN 1 ELSE 0 END) AS missing_customer_keys
FROM fact_sales;
