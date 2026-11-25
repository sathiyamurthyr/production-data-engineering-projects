/*
================================================================================
MODULE 46: Dimension Tables & Conformed Dimensions
================================================================================
1. EXPLANATION:
Dimension tables contain context attributes (customer details, product names, locations).
*/

SELECT 
    customer_key,
    customer_id,
    first_name,
    city,
    state
FROM dim_customers
WHERE is_current = 1;
