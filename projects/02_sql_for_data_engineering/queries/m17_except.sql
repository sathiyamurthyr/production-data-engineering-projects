/*
================================================================================
MODULE 17: EXCEPT / MINUS & Set Difference
================================================================================
1. EXPLANATION:
EXCEPT returns rows in the first query that do not exist in the second query.
*/

SELECT customer_key FROM dim_customers
EXCEPT
SELECT customer_key FROM fact_sales;
