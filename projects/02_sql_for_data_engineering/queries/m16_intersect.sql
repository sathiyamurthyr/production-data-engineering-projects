/*
================================================================================
MODULE 16: INTERSECT & Common Element Filtering
================================================================================
1. EXPLANATION:
INTERSECT returns only rows present in both result sets.
*/

SELECT customer_key FROM fact_sales
INTERSECT
SELECT customer_key FROM fact_orders;
