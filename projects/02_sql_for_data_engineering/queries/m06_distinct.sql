/*
================================================================================
MODULE 06: DISTINCT & Unique Set Selection
================================================================================
1. EXPLANATION:
DISTINCT triggers an implicit GROUP BY / Sort to remove duplicate tuples.
*/

SELECT DISTINCT 
    category,
    subcategory
FROM dim_products;
