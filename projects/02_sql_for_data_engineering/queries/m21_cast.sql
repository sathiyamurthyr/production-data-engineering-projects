/*
================================================================================
MODULE 21: CAST & Explicit Type Conversion
================================================================================
1. EXPLANATION:
CAST explicitly converts a value from one data type to another (`CAST(col AS INTEGER)`).
*/

SELECT 
    sales_id,
    net_amount,
    CAST(net_amount AS INTEGER) AS net_amount_int,
    CAST(sale_date AS TEXT) AS sale_date_str
FROM fact_sales;
