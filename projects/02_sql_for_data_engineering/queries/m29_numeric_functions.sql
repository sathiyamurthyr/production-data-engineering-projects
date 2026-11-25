/*
================================================================================
MODULE 29: Numeric & Mathematical Functions (ROUND, ABS, CEIL, FLOOR)
================================================================================
1. EXPLANATION:
Numeric functions round decimals, calculate absolute values, and compute financial metrics.
*/

SELECT 
    product_name,
    unit_price,
    cost_price,
    ROUND(unit_price - cost_price, 2) AS profit_margin,
    ROUND(((unit_price - cost_price) / unit_price) * 100, 2) AS profit_margin_pct
FROM dim_products;
