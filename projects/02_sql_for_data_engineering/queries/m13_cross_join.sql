/*
================================================================================
MODULE 13: Cross Join & Cartesian Products
================================================================================
1. EXPLANATION:
CROSS JOIN generates the Cartesian product (N x M rows). Used in DE to generate date-product grids for zero-filling missing aggregate metrics.
*/

SELECT 
    c.customer_id,
    p.product_id
FROM dim_customers AS c
CROSS JOIN dim_products AS p
LIMIT 10;
