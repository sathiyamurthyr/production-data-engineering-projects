/*
================================================================================
MODULE 27: Date & Time Manipulation Functions
================================================================================
1. EXPLANATION:
Date functions parse, format, extract parts (year, month, day), and calculate date diffs.
*/

SELECT 
    sales_id,
    sale_date,
    strftime('%Y', sale_date) AS sale_year,
    strftime('%m', sale_date) AS sale_month,
    strftime('%d', sale_date) AS sale_day
FROM fact_sales;
