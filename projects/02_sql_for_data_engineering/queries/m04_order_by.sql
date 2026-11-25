/*
================================================================================
MODULE 04: ORDER BY & Sorting Performance
================================================================================
1. EXPLANATION:
ORDER BY sorts output sets. In large data warehouses, sorting requires full shuffle spillage to disk unless indexed.
*/

SELECT 
    product_name,
    unit_price,
    category
FROM dim_products
ORDER BY unit_price DESC;
