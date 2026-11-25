/*
================================================================================
MODULE 02: SELECT Statement & Column Projection
================================================================================
1. EXPLANATION:
SELECT projects specific columns from tables. Avoid `SELECT *` in production to minimize memory and I/O.
*/

SELECT 
    customer_id,
    first_name,
    last_name,
    email,
    city
FROM dim_customers
WHERE is_current = 1;
