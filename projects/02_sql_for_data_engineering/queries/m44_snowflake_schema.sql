/*
================================================================================
MODULE 44: Snowflake Schema Architecture
================================================================================
1. EXPLANATION:
Snowflake Schema normalizes dimension tables into sub-dimensions (e.g., product -> subcategory -> category).
*/

SELECT 
    p.product_name,
    p.category,
    d.department_name
FROM dim_products p
CROSS JOIN dim_departments d;
