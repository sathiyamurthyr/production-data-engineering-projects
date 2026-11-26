/*
================================================================================
MODULE 19: NULL Handling & Three-Valued Logic
================================================================================
1. EXPLANATION:
NULL represents missing/unknown data in SQL. Comparisons with NULL yield UNKNOWN (`col = NULL` is invalid; use `col IS NULL`).
*/

SELECT 
    customer_id,
    first_name,
    email
FROM dim_customers
WHERE email IS NOT NULL;
