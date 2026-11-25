/*
================================================================================
MODULE 11: SQL Joins (INNER, LEFT, RIGHT, FULL)
================================================================================
1. EXPLANATION:
Joins combine columns from one or more tables based on join predicates.
*/

SELECT 
    c.customer_id,
    c.first_name || ' ' || c.last_name AS customer_name,
    s.transaction_id,
    s.net_amount
FROM dim_customers AS c
INNER JOIN fact_sales AS s ON c.customer_key = s.customer_key;
